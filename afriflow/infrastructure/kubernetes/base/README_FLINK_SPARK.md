# Flink & Spark Kubernetes Deployment Guide

## Overview

We provide production-grade Kubernetes manifests for Apache Flink (stream processing) and Apache Spark (batch processing) on the AfriFlow platform.

---

## Flink Session Cluster

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Flink Session Cluster                   │
│                                                          │
│  ┌─────────────┐                                        │
│  │ JobManager  │  Port 6123 (RPC)                       │
│  │   (1 pod)   │  Port 6124 (Blob Server)               │
│  │             │  Port 8081 (Web UI)                    │
│  │             │  Port 9249 (Metrics)                   │
│  └─────────────┘                                        │
│         │                                               │
│         ▼                                               │
│  ┌─────────────┐  ┌─────────────┐                      │
│  │ TaskManager │  │ TaskManager │                      │
│  │   (pod 1)   │  │   (pod 2)   │                      │
│  │ 4 Slots     │  │ 4 Slots     │                      │
│  │ 4 GiB RAM   │  │ 4 GiB RAM   │                      │
│  │ 2 CPU       │  │ 2 CPU       │                      │
│  └─────────────┘  └─────────────┘                      │
│                                                          │
│  Storage:                                                │
│  - Checkpoints: S3 (100 GiB)                            │
│  - Savepoints: S3 (50 GiB)                              │
│  - Storage: SSD (50 GiB)                                │
└─────────────────────────────────────────────────────────┘
```

### Deployment

```bash
# Apply Flink cluster manifests
kubectl apply -f infrastructure/kubernetes/base/flink-cluster.yml

# Verify deployment
kubectl get pods -n afriflow -l app=flink
kubectl get services -n afriflow -l app=flink
kubectl get pvc -n afriflow -l app=flink
kubectl get pdb -n afriflow -l app=flink

# Check JobManager logs
kubectl logs -n afriflow -l app.kubernetes.io/component=jobmanager -f

# Check TaskManager logs
kubectl logs -n afriflow -l app.kubernetes.io/component=taskmanager -f
```

### Validation

```bash
# Validate manifests with kubeval
kubeval infrastructure/kubernetes/base/flink-cluster.yml

# Dry-run server-side validation
kubectl apply -f infrastructure/kubernetes/base/flink-cluster.yml \
  --dry-run=server \
  --namespace=afriflow

# Check resource quotas
kubectl describe quota -n afriflow
```

### Accessing Flink Web UI

```bash
# Port-forward to JobManager
kubectl port-forward -n afriflow svc/flink-jobmanager 8081:8081

# Open browser to http://localhost:8081
# Default credentials: none (open in dev)
```

### Submitting Flink Jobs

```bash
# Using Flink CLI
kubectl run flink-cli --rm -it --image=flink:1.18.0 -- \
  flink run -m flink-jobmanager:8081 \
  /opt/flink/examples/streaming/WordCount.jar

# Using REST API
curl -X POST \
  -H "Content-Type: application/json" \
  --data-binary @job.json \
  http://localhost:8081/jars/upload

# Submit job
curl -X POST \
  -H "Content-Type: application/json" \
  --data-binary @job-spec.json \
  http://localhost:8081/jobs/submit
```

### Monitoring Flink

```bash
# Access Prometheus metrics
kubectl port-forward -n afriflow svc/flink-jobmanager 9249:9249
curl http://localhost:9249/metrics

# Key metrics to monitor:
# - flink_jobmanager_status
# - flink_taskmanager_status
# - flink_job_numTasks
# - flink_job_restarts
```

### Scaling TaskManagers

```bash
# Scale TaskManager replicas
kubectl scale deployment -n afriflow flink-taskmanager --replicas=5

# Verify scaling
kubectl get pods -n afriflow -l app.kubernetes.io/component=taskmanager
```

### High Availability Configuration

Flink HA is configured using Kubernetes services:

```yaml
high-availability: kubernetes
high-availability.storageDir: s3://afriflow-flink-ha/
high-availability.kubernetes.namespace: afriflow
high-availability.kubernetes.cluster-id: flink-session-cluster
```

For production, deploy multiple JobManagers with ZooKeeper:

```bash
# Deploy ZooKeeper
kubectl apply -f infrastructure/kubernetes/base/zookeeper.yml

# Update Flink config for HA
kubectl edit configmap -n afriflow flink-config
```

### Checkpoint & Savepoint Management

```bash
# Trigger savepoint via REST API
curl -X POST \
  -H "Content-Type: application/json" \
  http://localhost:8081/jobs/:jobid/savepoints \
  -d '{"target-directory": "s3://afriflow-flink-savepoints/"}'

# List checkpoints
kubectl get pods -n afriflow -l app=flink \
  -o jsonpath='{.items[*].spec.volumes[*].persistentVolumeClaim.claimName}'

# Check checkpoint storage
kubectl exec -n afriflow -it flink-jobmanager-xxxx -- \
  ls -la /var/flink/checkpoints
```

### Pod Disruption Budgets

PDBs ensure availability during updates:

```bash
# View PDB status
kubectl get pdb -n afriflow

# Test PDB (should maintain minAvailable)
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

---

## Spark Operator

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Spark Operator                          │
│                                                          │
│  ┌─────────────┐                                        │
│  │   Operator  │  Leader Election Enabled               │
│  │   (1 pod)   │  Webhook: Port 8080                    │
│  │             │  Metrics: Port 10254                   │
│  └─────────────┘                                        │
│         │                                               │
│         ▼                                               │
│  ┌─────────────────────────────────────────────┐       │
│  │         SparkApplication CRDs                │       │
│  │  - Python 3.9 Image                          │       │
│  │  - Dynamic Allocation                        │       │
│  │  - S3/HDFS Credentials                       │       │
│  │  - Prometheus Monitoring                     │       │
│  └─────────────────────────────────────────────┘       │
│                                                          │
│  Certificates: cert-manager integration                 │
│  RBAC: Namespace-scoped (afriflow)                      │
└─────────────────────────────────────────────────────────┘
```

### Deployment

```bash
# Install cert-manager (required for webhooks)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=Available deployment -n cert-manager --all --timeout=120s

# Apply Spark operator manifests
kubectl apply -f infrastructure/kubernetes/base/spark-operator.yml

# Verify deployment
kubectl get pods -n afriflow -l app=spark-operator
kubectl get services -n afriflow -l app=spark-operator
kubectl get certificates -n afriflow
kubectl get mutatingwebhookconfigurations
kubectl get validatingwebhookconfigurations
```

### Validation

```bash
# Validate manifests with kubeval
kubeval infrastructure/kubernetes/base/spark-operator.yml

# Dry-run server-side validation
kubectl apply -f infrastructure/kubernetes/base/spark-operator.yml \
  --dry-run=server \
  --namespace=afriflow

# Check webhook configurations
kubectl get mutatingwebhookconfigurations spark-operator-webhook -o yaml
kubectl get validatingwebhookconfigurations spark-operator-webhook -o yaml
```

### Accessing Operator Metrics

```bash
# Port-forward to operator
kubectl port-forward -n afriflow svc/spark-operator-webhook 10254:10254

# Access metrics
curl http://localhost:10254/metrics

# Key metrics:
# - spark_operator_sparkapplications_total
# - spark_operator_sparkapplications_running
# - spark_operator_sparkapplications_succeeded
# - spark_operator_sparkapplications_failed
```

### Submitting Spark Applications

```bash
# Create SparkApplication YAML
cat > spark-pi-job.yml <<EOF
apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication
metadata:
  name: spark-pi
  namespace: afriflow
spec:
  type: Python
  mode: cluster
  image: apache/spark:3.5.0-python3.9
  mainApplicationFile: local:///opt/spark/examples/src/main/python/pi.py
  sparkVersion: "3.5.0"
  driver:
    cores: 1
    memory: 2048m
  executor:
    cores: 2
    instances: 2
    memory: 4096m
  dynamicAllocation:
    enabled: true
    initialExecutors: 2
    minExecutors: 1
    maxExecutors: 10
EOF

# Submit application
kubectl apply -f spark-pi-job.yml

# Monitor application
kubectl get sparkapplications -n afriflow
kubectl describe sparkapplication spark-pi -n afriflow

# View driver logs
kubectl logs -n afriflow -l spark-role=driver -f

# View executor logs
kubectl logs -n afriflow -l spark-role=executor -f
```

### SparkApplication Lifecycle

```bash
# List all Spark applications
kubectl get sparkapplications -n afriflow

# Get application status
kubectl get sparkapplication spark-pi -n afriflow -o jsonpath='{.status.applicationState}'

# View application events
kubectl get events -n afriflow --field-selector involvedObject.name=spark-pi

# Delete application
kubectl delete sparkapplication spark-pi -n afriflow

# Cancel running application
kubectl patch sparkapplication spark-pi -n afriflow \
  --type='merge' \
  -p '{"spec":{"restartPolicy":{"type":"Never"}}}'
```

### Configuring S3/HDFS Access

```bash
# Create secret for AWS credentials
kubectl create secret generic spark-aws-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  --from-literal=AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  --from-literal=AWS_DEFAULT_REGION=af-south-1 \
  -n afriflow

# Update SparkApplication to use credentials
kubectl edit sparkapplication spark-pi -n afriflow
# Add volumeMounts and env as shown in template
```

### Dynamic Allocation

Dynamic allocation is enabled by default:

```yaml
dynamicAllocation:
  enabled: true
  initialExecutors: 2
  minExecutors: 1
  maxExecutors: 10
```

Monitor executor scaling:

```bash
# Watch executor pods
kubectl get pods -n afriflow -l spark-role=executor -w

# Check allocation metrics
kubectl port-forward -n afriflow svc/spark-operator-webhook 10254:10254
curl http://localhost:10254/metrics | grep spark_operator_executors
```

### Monitoring Spark Applications

```bash
# Access Spark UI (driver)
DRIVER_POD=$(kubectl get pods -n afriflow -l spark-role=driver -o jsonpath='{.items[0].metadata.name}')
kubectl port-forward -n afriflow $DRIVER_POD 4040:4040

# Open browser to http://localhost:4040

# Prometheus metrics
# Spark applications expose metrics on port 8090
kubectl port-forward -n afriflow $DRIVER_POD 8090:8090
curl http://localhost:8090/metrics
```

### Troubleshooting

#### Operator Not Starting

```bash
# Check operator logs
kubectl logs -n afriflow -l app=spark-operator -f

# Check certificate status
kubectl get certificates -n afriflow
kubectl describe certificate spark-webhook-cert -n afriflow

# Verify webhook service
kubectl get endpoints -n afriflow spark-operator-webhook
```

#### Application Stuck in Submitting State

```bash
# Check driver pod
kubectl get pods -n afriflow -l spark-role=driver

# Check driver logs
kubectl logs -n afriflow -l spark-role=driver --previous

# Check RBAC permissions
kubectl auth can-i create pods -n afriflow --as=system:serviceaccount:afriflow:spark-application
```

#### Webhook Failures

```bash
# Check webhook certificates
kubectl get secret spark-webhook-certs -n afriflow -o jsonpath='{.data}' | jq

# Renew certificates
kubectl delete certificate spark-webhook-cert -n afriflow
kubectl wait --for=condition=Ready certificate spark-webhook-cert -n afriflow --timeout=120s

# Restart operator
kubectl rollout restart deployment -n afriflow spark-operator
```

---

## Resource Quotas

### Flink Resources

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| JobManager | 1 core | 2 cores | 2 GiB | 4 GiB |
| TaskManager | 2 cores | 2 cores | 4 GiB | 4 GiB |
| JMX Exporter | 100m | 200m | 128 MiB | 256 MiB |

### Spark Operator Resources

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| Operator | 200m | 500m | 512 MiB | 1 GiB |
| Driver (default) | 1 core | 1 core | 2 GiB | 2 GiB |
| Executor (default) | 2 cores | 2 cores | 4 GiB | 4 GiB |

---

## Security Considerations

### Pod Security

- Run as non-root user (UID 9999 for Flink, 185 for Spark)
- Read-only root filesystem where possible
- Drop all capabilities
- No privilege escalation

### Network Security

- ClusterIP services only (no NodePort/LoadBalancer)
- Network policies restrict pod-to-pod communication
- TLS for webhook communication

### RBAC

- Service accounts per component
- Namespace-scoped permissions
- Least privilege principle

---

## Cost Optimization

### Flink

- Use TaskManager auto-scaling based on backlog
- Configure checkpoint intervals based on SLA
- Use incremental checkpoints for large state

### Spark

- Enable dynamic allocation
- Set appropriate min/max executors
- Use spot instances for executors (if available)

---

## Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| Platform Engineering | Thabo Kunene | 2026-03-17 | ✅ Complete |
| Operations | - | - | Pending |
| Security | - | - | Pending |

---

*Document Version: 1.0*  
*Last Updated: 2026-03-17*  
*Next Review: 2026-04-17*

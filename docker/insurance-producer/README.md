# AfriFlow Insurance Kafka Producer

Production-ready Kafka producer for insurance data ingestion with SSL/TLS support, Avro serialization, schema validation, and comprehensive monitoring.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Monitoring & Alerting](#monitoring--alerting)
- [Deployment](#deployment)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

The Insurance Kafka Producer is a production-ready component for ingesting insurance policy and claim data into Kafka topics. It provides:

- **Secure Connections**: SSL/TLS support for encrypted communication
- **Schema Validation**: Avro schema validation for data quality
- **Reliability**: Automatic retry with exponential backoff
- **Observability**: Comprehensive metrics and structured logging
- **Compliance**: POPIA-compliant data handling for South African regulations

## Features

### Core Features
- ✅ SSL/TLS secure connections
- ✅ Avro message serialization
- ✅ Schema validation against Avro schemas
- ✅ Automatic retry with exponential backoff
- ✅ Metrics collection (throughput, latency, error rates)
- ✅ Structured JSON logging
- ✅ Graceful shutdown

### Insurance-Specific Features
- ✅ Policy message type support
- ✅ Claim message type support
- ✅ POPIA compliance (PII hashing)
- ✅ Data classification headers
- ✅ Insurance schema evolution support

### Operational Features
- ✅ Docker containerization
- ✅ Kubernetes-ready
- ✅ Prometheus metrics export
- ✅ Health checks
- ✅ Multiple environment support (dev, staging, prod)

## Installation

### Prerequisites
- Python 3.9+
- Kafka broker (2.8+)
- Schema Registry (optional, for Avro)

### Install Dependencies

```bash
# Install from requirements
pip install -r requirements.txt

# Or install individually
pip install kafka-python fastavro
```

### Requirements File

```txt
# requirements.txt
kafka-python>=2.0.2
fastavro>=1.8.0
confluent-kafka>=2.0.0  # Optional, for high-performance producer
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (dev, staging, prod) | `dev` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker addresses | `localhost:9092` |
| `SCHEMA_REGISTRY_URL` | Schema Registry URL | `http://localhost:8081` |
| `KAFKA_SSL_ENABLED` | Enable SSL/TLS | `false` |
| `KAFKA_SSL_CAFILE` | CA certificate path | - |
| `KAFKA_SSL_CERTFILE` | Client certificate path | - |
| `KAFKA_SSL_KEYFILE` | Client key path | - |
| `KAFKA_SSL_PASSWORD` | Key password | - |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | Log format (json, text) | `json` |

### Configuration Classes

```python
from afriflow.domains.insurance.ingestion.kafka_producer import (
    ProducerConfig,
    SSLConfig,
    RetryConfig,
)

# Basic configuration
config = ProducerConfig(
    bootstrap_servers=["kafka1:9092", "kafka2:9092"],
    client_id="my-insurance-producer",
    acks="all",  # Wait for all replicas
    retries=5,
    compression_type="snappy",
)

# SSL configuration
config.ssl_config = SSLConfig(
    enabled=True,
    cafile="/path/to/ca.pem",
    certfile="/path/to/cert.pem",
    keyfile="/path/to/key.pem",
)

# Retry configuration
config.retry_config = RetryConfig(
    max_retries=5,
    initial_delay=0.1,
    max_delay=30.0,
    exponential_base=2.0,
)
```

## Usage

### Basic Usage

```python
from afriflow.domains.insurance.ingestion.kafka_producer import (
    InsuranceKafkaProducer,
    PolicyMessage,
    ClaimMessage,
)

# Create and connect producer
producer = InsuranceKafkaProducer()
producer.connect()

# Send a policy
policy = PolicyMessage(
    policy_id="POL-12345",
    policy_type="group_life",
    policyholder_id="EMP-001",
    insurer="Standard Bank Insurance",
    country="ZA",
    currency="ZAR",
    sum_assured=500000,
    annual_premium=12000,
    inception_date="2024-01-01",
    expiry_date="2025-01-01",
    status="active",
)

future = producer.send_policy(policy)
print(f"Policy sent: {policy.policy_id}")

# Send a claim
claim = ClaimMessage(
    claim_id="CLM-67890",
    policy_id="POL-12345",
    policyholder_id="EMP-001",
    claim_type="death",
    claimed_amount=500000,
    currency="ZAR",
    country="ZA",
    incident_date="2024-01-10",
    submitted_at="2024-01-15T10:00:00Z",
    status="pending",
)

future = producer.send_claim(claim)
print(f"Claim sent: {claim.claim_id}")

# Close connection
producer.close()
```

### With Callbacks

```python
def on_success(metadata, message):
    print(f"Message sent: partition={metadata.partition}, offset={metadata.offset}")

def on_error(error, message):
    print(f"Send failed: {error}")

producer.on_success(on_success)
producer.on_error(on_error)
```

### Batch Sending

```python
messages = [
    ("insurance.policies.v1", policy_dict1, "key1"),
    ("insurance.policies.v1", policy_dict2, "key2"),
    ("insurance.claims.v1", claim_dict1, "key3"),
]

result = producer.send_batch(messages)
print(f"Sent: {result['sent']}, Failed: {result['failed']}")
```

### Metrics

```python
metrics = producer.get_metrics()
print(f"Messages sent: {metrics['messages_sent']}")
print(f"Success rate: {metrics['success_rate']}%")
print(f"Avg latency: {metrics['avg_latency_ms']}ms")
```

## API Reference

### InsuranceKafkaProducer

#### Constructor
```python
InsuranceKafkaProducer(config: Optional[ProducerConfig] = None)
```

#### Methods

| Method | Description |
|--------|-------------|
| `connect()` | Establish connection to Kafka |
| `disconnect()` | Close connection |
| `close()` | Alias for disconnect() |
| `send_policy(policy, key)` | Send policy message |
| `send_claim(claim, key)` | Send claim message |
| `send_batch(messages)` | Send batch of messages |
| `on_success(callback)` | Register success callback |
| `on_error(callback)` | Register error callback |
| `get_metrics()` | Get current metrics |
| `flush(timeout_ms)` | Flush pending messages |

### PolicyMessage

```python
PolicyMessage(
    policy_id: str,
    policy_type: str,  # group_life, funeral_cover, vehicle, property, etc.
    policyholder_id: str,
    policyholder_golden_id: Optional[str],
    insurer: str,
    country: str,
    currency: str,
    sum_assured: float,
    annual_premium: float,
    inception_date: str,
    expiry_date: str,
    status: str,  # active, lapsed, expired, claimed, cancelled
    is_corporate: bool = False,
    employer_id: Optional[str] = None,
    employee_count_covered: Optional[int] = None,
)
```

### ClaimMessage

```python
ClaimMessage(
    claim_id: str,
    policy_id: str,
    policyholder_id: str,
    claim_type: str,  # death, disability, retrenchment, vehicle_accident, etc.
    claimed_amount: float,
    approved_amount: Optional[float],
    currency: str,
    country: str,
    incident_date: str,
    submitted_at: str,
    status: str,  # pending, under_review, approved, rejected, paid
    assessor_id: Optional[str] = None,
    rejection_reason: Optional[str] = None,
    paid_at: Optional[str] = None,
)
```

## Monitoring & Alerting

### Metrics Exported

| Metric | Type | Description |
|--------|------|-------------|
| `messages_sent_total` | Counter | Total messages sent successfully |
| `messages_failed_total` | Counter | Total messages failed |
| `bytes_sent_total` | Counter | Total bytes sent |
| `send_latency_seconds` | Histogram | Send latency distribution |
| `retry_total` | Counter | Total retry attempts |
| `errors_by_type` | Gauge | Errors categorized by type |

### Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'insurance-producer'
    static_configs:
      - targets: ['insurance-producer:8000']
    metrics_path: /metrics
```

### Alerting Rules

```yaml
# alerts.yml
groups:
  - name: insurance-producer
    rules:
      - alert: HighErrorRate
        expr: rate(messages_failed_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in insurance producer"
      
      - alert: ProducerDown
        expr: up{job="insurance-producer"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Insurance producer is down"
```

## Deployment

### Docker

```bash
# Build image
docker build -f docker/insurance-producer/Dockerfile -t afriflow/insurance-producer .

# Run container
docker run -d \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e SCHEMA_REGISTRY_URL=http://schema-registry:8081 \
  afriflow/insurance-producer
```

### Docker Compose

```bash
# Start all services
docker-compose -f docker/insurance-producer/docker-compose.yml up -d

# Start with monitoring
docker-compose -f docker/insurance-producer/docker-compose.yml --profile monitoring up -d

# Run tests
docker-compose -f docker/insurance-producer/docker-compose.yml --profile test up
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: insurance-producer
spec:
  replicas: 3
  selector:
    matchLabels:
      app: insurance-producer
  template:
    metadata:
      labels:
        app: insurance-producer
    spec:
      containers:
        - name: producer
          image: afriflow/insurance-producer:latest
          env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: "kafka:9092"
            - name: SCHEMA_REGISTRY_URL
              value: "http://schema-registry:8081"
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            exec:
              command: ["python", "-c", "print('OK')"]
            initialDelaySeconds: 30
            periodSeconds: 10
```

## Testing

### Unit Tests

```bash
# Run unit tests
pytest afriflow/tests/unit/insurance/test_kafka_producer.py -v

# Run with coverage
pytest afriflow/tests/unit/insurance/ -v --cov=afriflow.domains.insurance
```

### Integration Tests

```bash
# Start Kafka (requires Docker)
docker-compose -f docker/insurance-producer/docker-compose.yml up -d kafka schema-registry

# Run integration tests
pytest afriflow/tests/integration/insurance/ -v -m integration

# Cleanup
docker-compose -f docker/insurance-producer/docker-compose.yml down
```

## Troubleshooting

### Common Issues

#### Connection Refused
```
ConnectionError: Kafka connection failed: [Errno 111] Connection refused
```
**Solution**: Verify Kafka broker is running and accessible. Check `KAFKA_BOOTSTRAP_SERVERS`.

#### Schema Validation Failed
```
SchemaValidationError: Message validation failed
```
**Solution**: Ensure message fields match the Avro schema. Check required fields.

#### SSL Handshake Failed
```
ssl.SSLCertVerificationError: certificate verify failed
```
**Solution**: Verify CA certificate path. Set `KAFKA_SSL_CHECK_HOSTNAME=false` for testing.

### Debug Mode

```python
from afriflow.logging_config import setup_logging
setup_logging(level="DEBUG", json_format=False)
```

### Log Analysis

```bash
# Filter error logs
kubectl logs -l app=insurance-producer | grep ERROR

# View metrics
curl http://localhost:8000/metrics
```

---

## License

This project is for demonstration purposes only. It is not a sanctioned initiative of Standard Bank Group, MTN, or any affiliated entity.

## Author

Thabo Kunene - Data Engineering Portfolio

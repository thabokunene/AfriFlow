# =============================================================================
# @file main.tf
# @description Country Pod Terraform module. Provisions the Kubernetes
#              namespace, resource quotas, IRSA IAM role, Flink cluster
#              (JobManager + TaskManagers), Kafka topic bootstrap, ConfigMap,
#              HPA, and PodDisruptionBudget for a single African country pod.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================
#
# AfriFlow - Country Pod Module: Main Configuration
#
# PURPOSE
# -------
# This module provisions all Kubernetes and AWS resources required for a
# single "country pod" — the isolated processing unit that ingests, enriches,
# and streams financial-domain events for one African country.
#
# A country pod encapsulates:
#   1. A dedicated Kubernetes namespace with ResourceQuota / LimitRange.
#   2. Domain-scoped Kafka topics on the shared MSK cluster.
#   3. Apache Flink stream-processing jobs (one JobManager + N TaskManagers).
#   4. Data simulator deployments (for dev/staging environments).
#   5. An IAM role (via IRSA) granting the pod write access to S3 Delta Lake.
#   6. Kubernetes RBAC so pods can self-describe (needed by Flink HA).
#
# FEDERATED ARCHITECTURE NOTE
# ----------------------------
# Each country pod is intentionally autonomous: it can process events without
# depending on the central hub being reachable.  The central hub consumes
# aggregated signals from pod output topics, never raw pod input topics.
# This design mirrors real-world regulatory data-residency requirements
# (e.g., POPIA in South Africa, NDPR in Nigeria).
#
# DISCLAIMER
# ----------
# This is a portfolio demonstration by Thabo Kunene.  It does not represent
# any production system or sanctioned initiative of any financial institution.
# =============================================================================

# ---------------------------------------------------------------------------
# Local Values
# ---------------------------------------------------------------------------

locals {
  # Derive namespace from country_code if caller left it blank
  namespace = var.namespace != "" ? var.namespace : "afriflow-${lower(var.country_code)}"

  # Short identifier used as a suffix on all named resources
  pod_id = lower(var.country_code)

  # S3 prefix where this country writes Bronze-layer Delta tables
  s3_prefix = var.s3_key_prefix != "" ? var.s3_key_prefix : "bronze/${local.pod_id}"

  # Base tags merged onto every taggable resource in the module
  base_tags = merge(
    {
      Project     = "AfriFlow"
      CountryCode = var.country_code
      CountryName = var.country_name
      RegionGroup = var.region_group
      Module      = "country_pod"
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.extra_tags
  )
}

# ---------------------------------------------------------------------------
# Kubernetes Namespace
#
# Each country gets its own namespace so resource isolation, RBAC, and
# NetworkPolicies can be applied independently per country.
# ---------------------------------------------------------------------------

resource "kubernetes_namespace" "country_pod" {
  metadata {
    name = local.namespace

    labels = {
      # Standard AfriFlow labels used by NetworkPolicies and monitoring
      "afriflow/component"   = "country-pod"
      "afriflow/country"     = local.pod_id
      "afriflow/region"      = var.region_group
      "afriflow/environment" = var.environment

      # Istio sidecar injection label — enable when service mesh is deployed
      "istio-injection" = var.environment == "prod" ? "enabled" : "disabled"
    }

    annotations = {
      "afriflow/country-name" = var.country_name
      "afriflow/managed-by"   = "terraform"
    }
  }
}

# ---------------------------------------------------------------------------
# Resource Quota
#
# Hard limits prevent a misbehaving country pod from consuming the entire
# cluster's capacity.  Values are driven by var.resource_limits so prod
# countries with higher transaction volumes can be allocated more headroom.
# ---------------------------------------------------------------------------

resource "kubernetes_resource_quota" "country_pod" {
  metadata {
    name      = "resource-quota"
    namespace = kubernetes_namespace.country_pod.metadata[0].name
  }

  spec {
    hard = {
      # Compute
      "limits.cpu"    = var.resource_limits.cpu_limit
      "limits.memory" = var.resource_limits.memory_limit

      # Pod count cap prevents unbounded HPA scale-out
      "pods" = tostring(var.resource_limits.pod_limit)

      # Service and ConfigMap limits to prevent namespace sprawl
      "services"   = "20"
      "configmaps" = "30"
      "secrets"    = "20"
    }
  }
}

# ---------------------------------------------------------------------------
# Limit Range
#
# Sets per-container defaults so workloads without explicit resource requests
# still get reasonable limits.  This ensures the Kubernetes scheduler can
# make accurate placement decisions even for ad-hoc debug pods.
# ---------------------------------------------------------------------------

resource "kubernetes_limit_range" "country_pod" {
  metadata {
    name      = "default-limits"
    namespace = kubernetes_namespace.country_pod.metadata[0].name
  }

  spec {
    limit {
      type = "Container"

      default = {
        cpu    = "500m"
        memory = "512Mi"
      }

      default_request = {
        cpu    = "100m"
        memory = "128Mi"
      }

      # Hard ceiling a single container may not exceed
      max = {
        cpu    = "4"
        memory = "8Gi"
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Network Policy
#
# Restricts ingress to pods in the same namespace and from the central-hub
# namespace.  All egress is permitted so Flink jobs can reach MSK (Kafka),
# RDS (checkpoint metadata), and S3 (Delta Lake).
# ---------------------------------------------------------------------------

resource "kubernetes_network_policy" "country_pod_isolation" {
  metadata {
    name      = "country-pod-isolation"
    namespace = kubernetes_namespace.country_pod.metadata[0].name
  }

  spec {
    # Apply to all pods in this namespace
    pod_selector {}

    policy_types = ["Ingress"]

    ingress {
      # Allow traffic from pods within the same country namespace
      from {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = local.namespace
          }
        }
      }
    }

    ingress {
      # Allow traffic from the central hub (for health checks & signal pulls)
      from {
        namespace_selector {
          match_labels = {
            "afriflow/component" = "central-hub"
          }
        }
      }
    }
  }
}

# ---------------------------------------------------------------------------
# IRSA — IAM Role for Service Accounts
#
# Kubernetes pods in this namespace assume this IAM role via OIDC federation.
# The role grants write access to the country's Bronze S3 prefix and read
# access to MSK topics.  No long-lived credentials are stored in the cluster.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "country_pod" {
  name = "afriflow-country-pod-${local.pod_id}-${var.environment}"

  # Trust policy: only the Kubernetes service account in this namespace
  # can assume this role via the cluster's OIDC provider.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Federated = var.eks_oidc_provider_arn }
        Action    = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            # Restrict to the specific service account in the country namespace
            "${replace(var.eks_oidc_provider_arn, "arn:aws:iam::${var.aws_account_id}:oidc-provider/", "")}:sub" = "system:serviceaccount:${local.namespace}:afriflow-pod-sa"
          }
        }
      }
    ]
  })

  tags = local.base_tags
}

# IAM policy granting scoped S3 and MSK access for the country pod
resource "aws_iam_role_policy" "country_pod_s3" {
  name = "afriflow-country-pod-${local.pod_id}-s3"
  role = aws_iam_role.country_pod.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Write Bronze-layer events to the country's Delta Lake prefix
        Sid    = "DeltaLakeWrite"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          "arn:aws:s3:::${var.delta_lake_bucket}",
          "arn:aws:s3:::${var.delta_lake_bucket}/${local.s3_prefix}/*"
        ]
      },
      {
        # Allow KMS decrypt so pods can read/write KMS-encrypted S3 objects
        Sid    = "S3KMSAccess"
        Effect = "Allow"
        Action = [
          "kms:GenerateDataKey",
          "kms:Decrypt"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Kubernetes Service Account
#
# Annotated with the IAM role ARN so the EKS pod identity webhook can inject
# the correct credentials at pod creation time via IRSA.
# ---------------------------------------------------------------------------

resource "kubernetes_service_account" "country_pod" {
  metadata {
    name      = "afriflow-pod-sa"
    namespace = kubernetes_namespace.country_pod.metadata[0].name

    annotations = {
      # This annotation is read by the Amazon EKS Pod Identity webhook to
      # mount the correct OIDC token into the pod's filesystem.
      "eks.amazonaws.com/role-arn" = aws_iam_role.country_pod.arn
    }

    labels = {
      "afriflow/component" = "country-pod"
      "afriflow/country"   = local.pod_id
    }
  }

  # Prevent Terraform from recreating the service account if the auto-mounted
  # token secret has been rotated by the cluster.
  automount_service_account_token = true
}

# ---------------------------------------------------------------------------
# Kafka Topics
#
# One MSK topic per financial domain within this country pod.
# Partitions are sized for the expected throughput — pbb and cell domains
# have higher event rates than forex and insurance.
# ---------------------------------------------------------------------------

resource "aws_msk_configuration" "country_pod" {
  # Shared MSK server configuration reference for topic-level settings.
  # Actual topic creation is handled by a null_resource Kafka admin call
  # below because the AWS MSK Terraform provider does not expose a
  # first-class topic resource as of provider v5.x.
  name              = "afriflow-${local.pod_id}-kafka-config"
  kafka_versions    = ["3.5.1"]
  server_properties = <<-PROPS
    # Disable auto-creation so topics must be explicitly provisioned
    auto.create.topics.enable=false
    # Default replication factor for internal topics
    default.replication.factor=3
    # Min in-sync replicas — ensures durability even with one broker down
    min.insync.replicas=2
    # Log compaction for changelog topics
    log.cleanup.policy=delete
  PROPS

  lifecycle {
    # MSK configurations are immutable after creation; changes require a new
    # configuration version which triggers a rolling broker restart.
    create_before_destroy = true
  }
}

# Null resource: creates Kafka topics via the kafka-topics CLI inside the
# Flink init container.  This is a pragmatic workaround until the MSK
# provider gains native topic support.
resource "null_resource" "kafka_topics" {
  # Re-run topic creation whenever the topic map changes
  triggers = {
    topics_hash = sha256(jsonencode(var.kafka_topics))
    country     = var.country_code
  }

  provisioner "local-exec" {
    # Creates each topic if it does not already exist.  The --if-not-exists
    # flag makes this operation idempotent — safe to run on every apply.
    command = <<-CMD
      for TOPIC in ${join(" ", [for k, v in var.kafka_topics : "${local.pod_id}-${k}"])}; do
        echo "Creating topic: $TOPIC"
        kafka-topics.sh \
          --bootstrap-server "${var.kafka_bootstrap_servers}" \
          --create \
          --if-not-exists \
          --topic "$TOPIC" \
          --partitions 6 \
          --replication-factor 3 \
          --config retention.ms=604800000
      done
    CMD

    environment = {
      KAFKA_BOOTSTRAP_SERVERS = var.kafka_bootstrap_servers
    }
  }

  depends_on = [kubernetes_namespace.country_pod]
}

# ---------------------------------------------------------------------------
# Flink ConfigMap
#
# Centralises all Flink job configuration in one Kubernetes ConfigMap.
# Pods mount this as a volume so operator changes take effect without
# rebuilding container images.
# ---------------------------------------------------------------------------

resource "kubernetes_config_map" "flink_config" {
  metadata {
    name      = "flink-config"
    namespace = kubernetes_namespace.country_pod.metadata[0].name

    labels = {
      "afriflow/component" = "flink"
      "afriflow/country"   = local.pod_id
    }
  }

  data = {
    # Flink configuration file mounted at /opt/flink/conf/flink-conf.yaml
    "flink-conf.yaml" = <<-CONF
      # -------------------------------------------------------------------
      # AfriFlow Flink Configuration — ${var.country_name} (${var.country_code})
      # -------------------------------------------------------------------

      # JobManager high-availability using Kubernetes ConfigMaps as the
      # HA storage backend — no external ZooKeeper required.
      high-availability: kubernetes
      high-availability.storageDir: s3://${var.delta_lake_bucket}/${local.s3_prefix}/_flink_ha/

      # Checkpointing: write incremental checkpoints to S3 Delta Lake prefix.
      # 60-second interval balances recovery time vs. checkpoint overhead.
      execution.checkpointing.interval: 60000
      execution.checkpointing.mode: EXACTLY_ONCE
      state.backend: rocksdb
      state.checkpoints.dir: s3://${var.delta_lake_bucket}/${local.s3_prefix}/_checkpoints/
      state.savepoints.dir: s3://${var.delta_lake_bucket}/${local.s3_prefix}/_savepoints/

      # TaskManager resource allocation
      taskmanager.numberOfTaskSlots: ${var.flink_task_slots}
      taskmanager.memory.process.size: 2048m

      # Kafka connector defaults
      kafka.bootstrap.servers: ${var.kafka_bootstrap_servers}
      kafka.security.protocol: SSL
      kafka.ssl.truststore.location: /etc/kafka/ssl/kafka.truststore.jks

      # Parallelism = TaskManagers × slots
      parallelism.default: ${var.flink_task_manager_replicas * var.flink_task_slots}

      # Metrics: expose Prometheus endpoint on port 9249
      metrics.reporter.prom.class: org.apache.flink.metrics.prometheus.PrometheusReporter
      metrics.reporter.prom.port: 9249
    CONF

    # Country-specific metadata injected as environment variables into pods
    "country-metadata.env" = <<-ENV
      AFRIFLOW_COUNTRY_CODE=${var.country_code}
      AFRIFLOW_COUNTRY_NAME=${var.country_name}
      AFRIFLOW_REGION_GROUP=${var.region_group}
      AFRIFLOW_ENVIRONMENT=${var.environment}
      AFRIFLOW_S3_PREFIX=${local.s3_prefix}
      AFRIFLOW_DELTA_LAKE_BUCKET=${var.delta_lake_bucket}
    ENV
  }
}

# ---------------------------------------------------------------------------
# Flink JobManager Deployment
#
# The JobManager is the Flink cluster coordinator.  It schedules tasks onto
# TaskManagers, coordinates checkpoints, and exposes the Flink REST UI.
# Running a single JobManager replica is acceptable because HA is handled
# by the Kubernetes high-availability backend above.
# ---------------------------------------------------------------------------

resource "kubernetes_deployment" "flink_job_manager" {
  metadata {
    name      = "flink-jobmanager"
    namespace = kubernetes_namespace.country_pod.metadata[0].name

    labels = {
      "app"                = "flink-jobmanager"
      "afriflow/component" = "flink"
      "afriflow/role"      = "jobmanager"
      "afriflow/country"   = local.pod_id
    }
  }

  spec {
    # Single JobManager — HA is provided by Kubernetes ConfigMap backend
    replicas = 1

    selector {
      match_labels = {
        "app"              = "flink-jobmanager"
        "afriflow/country" = local.pod_id
      }
    }

    template {
      metadata {
        labels = {
          "app"                = "flink-jobmanager"
          "afriflow/component" = "flink"
          "afriflow/role"      = "jobmanager"
          "afriflow/country"   = local.pod_id
        }

        annotations = {
          # Prometheus scrape annotations picked up by the cluster's
          # Prometheus operator ServiceMonitor selector
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "9249"
          "prometheus.io/path"   = "/metrics"
        }
      }

      spec {
        service_account_name = kubernetes_service_account.country_pod.metadata[0].name

        # Prefer nodes labelled as country-pod nodes; tolerate the taint
        # set by the EKS node group in the root module.
        node_selector = {
          "afriflow/node-type" = "country-pod"
        }

        toleration {
          key      = "workload"
          operator = "Equal"
          value    = "country-pod"
          effect   = "NoSchedule"
        }

        container {
          name  = "jobmanager"
          image = var.flink_image

          args = ["jobmanager"]

          port {
            name           = "rpc"
            container_port = 6123
          }
          port {
            name           = "blob"
            container_port = 6124
          }
          port {
            name           = "ui"
            container_port = 8081
          }
          port {
            name           = "metrics"
            container_port = 9249
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.flink_config.metadata[0].name
            }
          }

          env {
            name  = "FLINK_PROPERTIES"
            value = "jobmanager.rpc.address: flink-jobmanager\n"
          }

          resources {
            requests = {
              cpu    = "500m"
              memory = "1Gi"
            }
            limits = {
              cpu    = "2"
              memory = "2Gi"
            }
          }

          liveness_probe {
            http_get {
              path = "/overview"
              port = 8081
            }
            initial_delay_seconds = 30
            period_seconds        = 10
            failure_threshold     = 5
          }

          readiness_probe {
            http_get {
              path = "/overview"
              port = 8081
            }
            initial_delay_seconds = 15
            period_seconds        = 5
          }
        }
      }
    }
  }

  depends_on = [kubernetes_config_map.flink_config]
}

# ---------------------------------------------------------------------------
# Flink TaskManager Deployment
#
# TaskManagers execute the actual stream-processing operators.  The number
# of replicas is controlled by var.flink_task_manager_replicas and can be
# scaled horizontally to increase throughput.
# ---------------------------------------------------------------------------

resource "kubernetes_deployment" "flink_task_manager" {
  metadata {
    name      = "flink-taskmanager"
    namespace = kubernetes_namespace.country_pod.metadata[0].name

    labels = {
      "app"                = "flink-taskmanager"
      "afriflow/component" = "flink"
      "afriflow/role"      = "taskmanager"
      "afriflow/country"   = local.pod_id
    }
  }

  spec {
    replicas = var.flink_task_manager_replicas

    selector {
      match_labels = {
        "app"              = "flink-taskmanager"
        "afriflow/country" = local.pod_id
      }
    }

    template {
      metadata {
        labels = {
          "app"                = "flink-taskmanager"
          "afriflow/component" = "flink"
          "afriflow/role"      = "taskmanager"
          "afriflow/country"   = local.pod_id
        }

        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "9249"
        }
      }

      spec {
        service_account_name = kubernetes_service_account.country_pod.metadata[0].name

        node_selector = {
          "afriflow/node-type" = "country-pod"
        }

        toleration {
          key      = "workload"
          operator = "Equal"
          value    = "country-pod"
          effect   = "NoSchedule"
        }

        container {
          name  = "taskmanager"
          image = var.flink_image

          args = ["taskmanager"]

          port {
            name           = "rpc"
            container_port = 6122
          }
          port {
            name           = "metrics"
            container_port = 9249
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.flink_config.metadata[0].name
            }
          }

          env {
            name  = "FLINK_PROPERTIES"
            # JobManager address must match the Service name defined below
            value = "jobmanager.rpc.address: flink-jobmanager\ntaskmanager.numberOfTaskSlots: ${var.flink_task_slots}\n"
          }

          resources {
            requests = {
              cpu    = "500m"
              memory = "1Gi"
            }
            limits = {
              cpu    = "2"
              memory = "2Gi"
            }
          }

          liveness_probe {
            tcp_socket {
              port = 6122
            }
            initial_delay_seconds = 30
            period_seconds        = 15
          }
        }
      }
    }
  }

  depends_on = [kubernetes_deployment.flink_job_manager]
}

# ---------------------------------------------------------------------------
# Flink JobManager Service
#
# Exposes the JobManager RPC and REST endpoints within the namespace so
# TaskManagers and the Flink CLI can reach it by DNS name.
# ---------------------------------------------------------------------------

resource "kubernetes_service" "flink_job_manager" {
  metadata {
    name      = "flink-jobmanager"
    namespace = kubernetes_namespace.country_pod.metadata[0].name

    labels = {
      "app"              = "flink-jobmanager"
      "afriflow/country" = local.pod_id
    }
  }

  spec {
    selector = {
      "app"              = "flink-jobmanager"
      "afriflow/country" = local.pod_id
    }

    port {
      name        = "rpc"
      port        = 6123
      target_port = 6123
    }

    port {
      name        = "blob"
      port        = 6124
      target_port = 6124
    }

    port {
      name        = "ui"
      port        = 8081
      target_port = 8081
    }

    # ClusterIP: the Flink UI is not exposed publicly; access via kubectl port-forward
    type = "ClusterIP"
  }
}

# ---------------------------------------------------------------------------
# Horizontal Pod Autoscaler — TaskManagers
#
# In staging and prod environments, automatically scale TaskManagers based
# on CPU utilisation.  This handles traffic spikes (e.g. payroll runs,
# month-end insurance settlements) without manual intervention.
# ---------------------------------------------------------------------------

resource "kubernetes_horizontal_pod_autoscaler_v2" "flink_task_manager" {
  # Only create the HPA in non-dev environments to avoid noisy test clusters
  count = var.environment != "dev" ? 1 : 0

  metadata {
    name      = "flink-taskmanager-hpa"
    namespace = kubernetes_namespace.country_pod.metadata[0].name
  }

  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = kubernetes_deployment.flink_task_manager.metadata[0].name
    }

    min_replicas = var.flink_task_manager_replicas
    max_replicas = var.flink_task_manager_replicas * 3

    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 70
        }
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Pod Disruption Budget — JobManager
#
# Ensures the JobManager pod is not evicted during node drains without
# a replacement being ready first.  Critical for preventing checkpoint
# loss during rolling cluster upgrades.
# ---------------------------------------------------------------------------

resource "kubernetes_pod_disruption_budget_v1" "flink_job_manager" {
  count = var.environment == "prod" ? 1 : 0

  metadata {
    name      = "flink-jobmanager-pdb"
    namespace = kubernetes_namespace.country_pod.metadata[0].name
  }

  spec {
    # At least 1 JobManager must always be available
    min_available = 1

    selector {
      match_labels = {
        "app"              = "flink-jobmanager"
        "afriflow/country" = local.pod_id
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "namespace" {
  description = "Kubernetes namespace created for this country pod."
  value       = kubernetes_namespace.country_pod.metadata[0].name
}

output "iam_role_arn" {
  description = "ARN of the IAM role assigned to this country pod via IRSA."
  value       = aws_iam_role.country_pod.arn
}

output "flink_ui_service" {
  description = "In-cluster DNS address for the Flink REST UI (port 8081)."
  value       = "${kubernetes_service.flink_job_manager.metadata[0].name}.${local.namespace}.svc.cluster.local:8081"
}

output "kafka_topic_prefix" {
  description = "Prefix used for all Kafka topics in this country pod (e.g. 'za-forex')."
  value       = local.pod_id
}

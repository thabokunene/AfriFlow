# =============================================================================
# @file main.tf
# @description Central Hub Terraform module. Provisions the Kubernetes
#              namespace, IRSA IAM role, Entity Resolution service, Cross-Domain
#              Signal processor, Data Shadow CronJob, and Client Briefing API
#              with optional public ALB Ingress.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================
#
# AfriFlow - Central Hub Module: Main Configuration
#
# PURPOSE
# -------
# The central hub aggregates enriched data from all country pods and runs the
# platform's cross-cutting intelligence services:
#
#   1. Entity Resolution    — matches a single corporate or retail client
#                             across multiple country pods using fuzzy name
#                             matching, document-number linking, and an ML
#                             confidence scorer.
#
#   2. Cross-Domain Signals — joins events from forex, PBB, insurance, and
#                             cell domains to detect composite business
#                             signals (e.g. a company expanding into a new
#                             country shows up simultaneously as a forex
#                             conversion, a new business-account opening, and
#                             a fleet of new SIM activations).
#
#   3. Data Shadow Model    — maintains a probabilistic representation of
#                             client economic activity that cannot be directly
#                             observed (e.g. informal-sector cash flows
#                             inferred from M-PESA patterns).
#
#   4. Client Briefing API  — REST API consumed by relationship managers.
#                             Returns a synthesised talking-points pack for a
#                             given client, combining all signals above.
#
# ARCHITECTURE NOTES
# ------------------
# * The hub never writes to country-pod Bronze prefixes.
# * All inter-service communication is via Kafka topics (async) or the
#   PostgreSQL metadata DB (synchronous lookups).
# * IRSA is used for all S3 and RDS access — no static credentials.
#
# DISCLAIMER
# ----------
# Portfolio demonstration by Thabo Kunene.  Not production-ready.
# =============================================================================

# ---------------------------------------------------------------------------
# Local Values
# ---------------------------------------------------------------------------

locals {
  base_tags = merge(
    {
      Project     = "AfriFlow"
      Component   = "central-hub"
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.extra_tags
  )

  # Kafka topic names consumed and produced by the hub
  input_topic_pattern  = "^(${join("|", [for c in var.active_country_codes : lower(c)])})-(forex|pbb|insurance|cell)-enriched$"
  output_topic_cross   = "afriflow-cross-domain-signals"
  output_topic_entity  = "afriflow-entity-resolution-events"
  output_topic_briefing = "afriflow-client-briefing-requests"
}

# ---------------------------------------------------------------------------
# Kubernetes Namespace
# ---------------------------------------------------------------------------

resource "kubernetes_namespace" "central_hub" {
  metadata {
    name = var.namespace

    labels = {
      "afriflow/component"   = "central-hub"
      "afriflow/environment" = var.environment
      # Istio sidecar injection: enabled in prod for mTLS between hub services
      "istio-injection" = var.environment == "prod" ? "enabled" : "disabled"
    }

    annotations = {
      "afriflow/managed-by" = "terraform"
      "afriflow/purpose"    = "Cross-country aggregation and intelligence services"
    }
  }
}

# ---------------------------------------------------------------------------
# Resource Quota
#
# The hub runs heavier workloads than individual country pods (entity
# resolution ML scoring is CPU-intensive) so it gets a larger allocation.
# ---------------------------------------------------------------------------

resource "kubernetes_resource_quota" "central_hub" {
  metadata {
    name      = "resource-quota"
    namespace = kubernetes_namespace.central_hub.metadata[0].name
  }

  spec {
    hard = {
      "limits.cpu"    = var.environment == "prod" ? "32" : "16"
      "limits.memory" = var.environment == "prod" ? "64Gi" : "32Gi"
      "pods"          = "50"
      "services"      = "30"
      "configmaps"    = "50"
    }
  }
}

# ---------------------------------------------------------------------------
# Network Policy
#
# The central hub must receive traffic from country pods (for signal queries)
# and expose the client briefing API to the Ingress controller.
# ---------------------------------------------------------------------------

resource "kubernetes_network_policy" "central_hub" {
  metadata {
    name      = "central-hub-netpol"
    namespace = kubernetes_namespace.central_hub.metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress"]

    ingress {
      # Intra-hub: all pods within the central namespace can talk to each other
      from {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = var.namespace
          }
        }
      }
    }

    ingress {
      # Country pods may call the entity resolution health-check endpoint
      from {
        namespace_selector {
          match_labels = {
            "afriflow/component" = "country-pod"
          }
        }
        pod_selector {
          match_labels = {
            "afriflow/role" = "flink"
          }
        }
      }
    }

    ingress {
      # ALB / Ingress controller traffic for the client briefing API
      from {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = "kube-system"
          }
        }
      }
    }
  }
}

# ---------------------------------------------------------------------------
# IRSA — IAM Role for Central Hub Service Account
#
# Grants the hub read access to all country pod S3 prefixes and read/write
# access to the Gold-layer hub prefix.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "central_hub" {
  name = "afriflow-central-hub-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Federated = var.eks_oidc_provider_arn }
        Action    = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(var.eks_oidc_provider_arn, "arn:aws:iam::${var.aws_account_id}:oidc-provider/", "")}:sub" = "system:serviceaccount:${var.namespace}:afriflow-hub-sa"
          }
        }
      }
    ]
  })

  tags = local.base_tags
}

resource "aws_iam_role_policy" "central_hub_s3" {
  name = "afriflow-central-hub-s3-${var.environment}"
  role = aws_iam_role.central_hub.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Read Silver-layer data from all country pod prefixes
        Sid    = "ReadBronzeSilver"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"]
        Resource = [
          "arn:aws:s3:::${var.delta_lake_bucket}",
          "arn:aws:s3:::${var.delta_lake_bucket}/bronze/*",
          "arn:aws:s3:::${var.delta_lake_bucket}/silver/*"
        ]
      },
      {
        # Write Gold-layer cross-domain signal tables
        Sid    = "WriteGold"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.delta_lake_bucket}",
          "arn:aws:s3:::${var.delta_lake_bucket}/${var.hub_s3_prefix}/*"
        ]
      },
      {
        # KMS decrypt/encrypt for all S3 operations via the shared KMS key
        Sid    = "KMSAccess"
        Effect = "Allow"
        Action = ["kms:GenerateDataKey", "kms:Decrypt"]
        Resource = ["*"]
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
# ---------------------------------------------------------------------------

resource "kubernetes_service_account" "central_hub" {
  metadata {
    name      = "afriflow-hub-sa"
    namespace = kubernetes_namespace.central_hub.metadata[0].name

    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.central_hub.arn
    }

    labels = {
      "afriflow/component" = "central-hub"
    }
  }

  automount_service_account_token = true
}

# ---------------------------------------------------------------------------
# Hub ConfigMap
#
# Central configuration shared by all hub services.  Mounted as a volume
# so values can be updated without redeploying container images.
# ---------------------------------------------------------------------------

resource "kubernetes_config_map" "hub_config" {
  metadata {
    name      = "hub-config"
    namespace = kubernetes_namespace.central_hub.metadata[0].name
  }

  data = {
    "hub.env" = <<-ENV
      AFRIFLOW_ENVIRONMENT=${var.environment}
      AFRIFLOW_KAFKA_BOOTSTRAP=${var.kafka_bootstrap_servers}
      AFRIFLOW_RDS_HOST=${split(":", var.rds_endpoint)[0]}
      AFRIFLOW_RDS_PORT=${length(split(":", var.rds_endpoint)) > 1 ? split(":", var.rds_endpoint)[1] : "5432"}
      AFRIFLOW_RDS_DB=${var.rds_database_name}
      AFRIFLOW_RDS_USER=${var.rds_username}
      AFRIFLOW_S3_BUCKET=${var.delta_lake_bucket}
      AFRIFLOW_S3_HUB_PREFIX=${var.hub_s3_prefix}
      AFRIFLOW_ACTIVE_COUNTRIES=${join(",", var.active_country_codes)}
      AFRIFLOW_OUTPUT_TOPIC_CROSS_DOMAIN=${local.output_topic_cross}
      AFRIFLOW_OUTPUT_TOPIC_ENTITY=${local.output_topic_entity}
      AFRIFLOW_OUTPUT_TOPIC_BRIEFING=${local.output_topic_briefing}
    ENV
  }
}

# ---------------------------------------------------------------------------
# Entity Resolution Service
#
# Matches client identifiers across country pods to build a unified Golden
# Record.  Uses probabilistic record linkage with configurable thresholds.
# Consumes country pod output topics; emits matched entity events to the
# entity resolution Kafka topic.
# ---------------------------------------------------------------------------

resource "kubernetes_deployment" "entity_resolution" {
  metadata {
    name      = "entity-resolution"
    namespace = kubernetes_namespace.central_hub.metadata[0].name

    labels = {
      "app"                = "entity-resolution"
      "afriflow/component" = "central-hub"
      "afriflow/service"   = "entity-resolution"
    }
  }

  spec {
    replicas = var.entity_resolution_replicas

    selector {
      match_labels = {
        "app" = "entity-resolution"
      }
    }

    # Rolling update: update one pod at a time so resolution never drops
    strategy {
      type = "RollingUpdate"
      rolling_update {
        max_unavailable = 0
        max_surge       = 1
      }
    }

    template {
      metadata {
        labels = {
          "app"                = "entity-resolution"
          "afriflow/component" = "central-hub"
          "afriflow/service"   = "entity-resolution"
          "version"            = var.hub_image_tag
        }

        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "8080"
          "prometheus.io/path"   = "/metrics"
        }
      }

      spec {
        service_account_name = kubernetes_service_account.central_hub.metadata[0].name

        # Schedule on central-hub node group, not country-pod nodes
        node_selector = {
          "afriflow/node-type" = "central-hub"
        }

        container {
          name  = "entity-resolution"
          image = "${var.hub_image_registry}/afriflow-entity-resolution:${var.hub_image_tag}"

          port {
            name           = "http"
            container_port = 8080
          }
          port {
            name           = "metrics"
            container_port = 9090
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.hub_config.metadata[0].name
            }
          }

          env {
            name = "AFRIFLOW_RDS_PASSWORD"
            value_from {
              secret_key_ref {
                # Secret created out-of-band; not managed by Terraform to
                # keep credentials out of the state file.
                name = "afriflow-rds-credentials"
                key  = "password"
              }
            }
          }

          resources {
            requests = {
              cpu    = "500m"
              memory = "1Gi"
            }
            limits = {
              cpu    = "4"
              memory = "4Gi"
            }
          }

          liveness_probe {
            http_get {
              path = "/healthz"
              port = 8080
            }
            initial_delay_seconds = 30
            period_seconds        = 15
          }

          readiness_probe {
            http_get {
              path = "/readyz"
              port = 8080
            }
            initial_delay_seconds = 10
            period_seconds        = 5
          }
        }
      }
    }
  }

  depends_on = [kubernetes_config_map.hub_config]
}

resource "kubernetes_service" "entity_resolution" {
  metadata {
    name      = "entity-resolution"
    namespace = kubernetes_namespace.central_hub.metadata[0].name
  }

  spec {
    selector = { "app" = "entity-resolution" }

    port {
      name        = "http"
      port        = 80
      target_port = 8080
    }

    type = "ClusterIP"
  }
}

# ---------------------------------------------------------------------------
# Cross-Domain Signal Processor
#
# Flink-based stream processor that joins enriched events from all country
# pods and emits composite business signals.  Key signals include:
#   - Expansion Signal  : correlated forex + PBB + cell activity
#   - Payroll Drift     : PBB payroll patterns diverging from seasonal norm
#   - Claims Spike      : insurance claims clustering by geography/product
# ---------------------------------------------------------------------------

resource "kubernetes_deployment" "cross_domain_signals" {
  metadata {
    name      = "cross-domain-signals"
    namespace = kubernetes_namespace.central_hub.metadata[0].name

    labels = {
      "app"              = "cross-domain-signals"
      "afriflow/service" = "cross-domain-signals"
    }
  }

  spec {
    replicas = var.cross_domain_signal_replicas

    selector {
      match_labels = {
        "app" = "cross-domain-signals"
      }
    }

    template {
      metadata {
        labels = {
          "app"              = "cross-domain-signals"
          "afriflow/service" = "cross-domain-signals"
        }

        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "9249"
        }
      }

      spec {
        service_account_name = kubernetes_service_account.central_hub.metadata[0].name

        node_selector = {
          "afriflow/node-type" = "central-hub"
        }

        container {
          name  = "cross-domain-signals"
          image = "${var.hub_image_registry}/afriflow-cross-domain:${var.hub_image_tag}"

          port {
            container_port = 9249
            name           = "metrics"
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.hub_config.metadata[0].name
            }
          }

          resources {
            requests = {
              cpu    = "1"
              memory = "2Gi"
            }
            limits = {
              cpu    = "4"
              memory = "8Gi"
            }
          }

          liveness_probe {
            tcp_socket {
              port = 9249
            }
            initial_delay_seconds = 45
            period_seconds        = 20
          }
        }
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Data Shadow Service
#
# Maintains probabilistic models of unobservable economic activity.
# Reads Gold-layer Delta tables; writes shadow model outputs back to S3.
# Runs as a batch-style Deployment (not a Kafka consumer) — triggered
# nightly via a Kubernetes CronJob.
# ---------------------------------------------------------------------------

resource "kubernetes_cron_job_v1" "data_shadow" {
  metadata {
    name      = "data-shadow-model"
    namespace = kubernetes_namespace.central_hub.metadata[0].name
  }

  spec {
    # Run at 02:00 UTC daily — off-peak for most African time zones
    schedule                      = "0 2 * * *"
    concurrency_policy            = "Forbid"   # Never run two instances simultaneously
    successful_jobs_history_limit = 3
    failed_jobs_history_limit     = 3

    job_template {
      metadata {}

      spec {
        # Fail the job if it hasn't completed within 4 hours
        active_deadline_seconds = 14400

        template {
          metadata {}

          spec {
            service_account_name = kubernetes_service_account.central_hub.metadata[0].name
            restart_policy       = "OnFailure"

            node_selector = {
              "afriflow/node-type" = "central-hub"
            }

            container {
              name  = "data-shadow"
              image = "${var.hub_image_registry}/afriflow-data-shadow:${var.hub_image_tag}"

              env_from {
                config_map_ref {
                  name = kubernetes_config_map.hub_config.metadata[0].name
                }
              }

              resources {
                requests = {
                  cpu    = "2"
                  memory = "4Gi"
                }
                limits = {
                  cpu    = "8"
                  memory = "16Gi"
                }
              }
            }
          }
        }
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Client Briefing API
#
# REST service consumed by relationship managers.  Aggregates entity
# resolution, cross-domain signals, and data shadow outputs into a
# structured talking-points response for a given client ID.
# ---------------------------------------------------------------------------

resource "kubernetes_deployment" "client_briefing" {
  metadata {
    name      = "client-briefing"
    namespace = kubernetes_namespace.central_hub.metadata[0].name

    labels = {
      "app"              = "client-briefing"
      "afriflow/service" = "client-briefing"
    }
  }

  spec {
    replicas = var.client_briefing_replicas

    selector {
      match_labels = {
        "app" = "client-briefing"
      }
    }

    strategy {
      type = "RollingUpdate"
      rolling_update {
        # Zero-downtime deploys: never take all pods offline simultaneously
        max_unavailable = 0
        max_surge       = 1
      }
    }

    template {
      metadata {
        labels = {
          "app"              = "client-briefing"
          "afriflow/service" = "client-briefing"
          "version"          = var.hub_image_tag
        }

        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "8080"
        }
      }

      spec {
        service_account_name = kubernetes_service_account.central_hub.metadata[0].name

        node_selector = {
          "afriflow/node-type" = "central-hub"
        }

        container {
          name  = "client-briefing"
          image = "${var.hub_image_registry}/afriflow-client-briefing:${var.hub_image_tag}"

          port {
            name           = "http"
            container_port = 8080
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.hub_config.metadata[0].name
            }
          }

          env {
            name = "AFRIFLOW_RDS_PASSWORD"
            value_from {
              secret_key_ref {
                name = "afriflow-rds-credentials"
                key  = "password"
              }
            }
          }

          resources {
            requests = {
              cpu    = "250m"
              memory = "512Mi"
            }
            limits = {
              cpu    = "2"
              memory = "2Gi"
            }
          }

          liveness_probe {
            http_get {
              path = "/healthz"
              port = 8080
            }
            initial_delay_seconds = 20
            period_seconds        = 10
          }

          readiness_probe {
            http_get {
              path = "/readyz"
              port = 8080
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "client_briefing" {
  metadata {
    name      = "client-briefing"
    namespace = kubernetes_namespace.central_hub.metadata[0].name
  }

  spec {
    selector = { "app" = "client-briefing" }

    port {
      name        = "http"
      port        = 80
      target_port = 8080
    }

    # NodePort so the ALB Ingress Controller can route traffic to it.
    # In internal-only deployments this stays ClusterIP.
    type = var.enable_public_api ? "NodePort" : "ClusterIP"
  }
}

# ---------------------------------------------------------------------------
# Kubernetes Ingress (ALB)
#
# Only created when var.enable_public_api = true.
# Uses the AWS Load Balancer Controller annotations to provision an
# Internet-facing ALB with HTTPS termination.
# ---------------------------------------------------------------------------

resource "kubernetes_ingress_v1" "client_briefing" {
  count = var.enable_public_api ? 1 : 0

  metadata {
    name      = "client-briefing-ingress"
    namespace = kubernetes_namespace.central_hub.metadata[0].name

    annotations = {
      # AWS Load Balancer Controller annotations
      "kubernetes.io/ingress.class"                        = "alb"
      "alb.ingress.kubernetes.io/scheme"                   = "internet-facing"
      "alb.ingress.kubernetes.io/target-type"              = "ip"
      "alb.ingress.kubernetes.io/listen-ports"             = jsonencode([{ HTTPS = 443 }])
      "alb.ingress.kubernetes.io/certificate-arn"          = var.alb_certificate_arn
      "alb.ingress.kubernetes.io/ssl-policy"               = "ELBSecurityPolicy-TLS13-1-2-2021-06"
      "alb.ingress.kubernetes.io/healthcheck-path"         = "/healthz"
      "alb.ingress.kubernetes.io/healthcheck-interval-seconds" = "15"
      "alb.ingress.kubernetes.io/load-balancer-attributes" = "idle_timeout.timeout_seconds=60"
    }
  }

  spec {
    rule {
      host = var.api_domain_name

      http {
        path {
          path      = "/api/v1/briefing"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service.client_briefing.metadata[0].name
              port {
                number = 80
              }
            }
          }
        }
      }
    }
  }
}

# ---------------------------------------------------------------------------
# HPA — Entity Resolution
#
# Entity resolution load spikes during month-end reporting windows when
# relationship managers run bulk client lookups.  HPA handles this without
# manual intervention.
# ---------------------------------------------------------------------------

resource "kubernetes_horizontal_pod_autoscaler_v2" "entity_resolution" {
  count = var.environment != "dev" ? 1 : 0

  metadata {
    name      = "entity-resolution-hpa"
    namespace = kubernetes_namespace.central_hub.metadata[0].name
  }

  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = kubernetes_deployment.entity_resolution.metadata[0].name
    }

    min_replicas = var.entity_resolution_replicas
    max_replicas = var.entity_resolution_replicas * 4

    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 65
        }
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Pod Disruption Budgets (prod only)
# ---------------------------------------------------------------------------

resource "kubernetes_pod_disruption_budget_v1" "entity_resolution" {
  count = var.environment == "prod" ? 1 : 0

  metadata {
    name      = "entity-resolution-pdb"
    namespace = kubernetes_namespace.central_hub.metadata[0].name
  }

  spec {
    min_available = 1

    selector {
      match_labels = { "app" = "entity-resolution" }
    }
  }
}

resource "kubernetes_pod_disruption_budget_v1" "client_briefing" {
  count = var.environment == "prod" ? 1 : 0

  metadata {
    name      = "client-briefing-pdb"
    namespace = kubernetes_namespace.central_hub.metadata[0].name
  }

  spec {
    min_available = 1

    selector {
      match_labels = { "app" = "client-briefing" }
    }
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "namespace" {
  description = "Kubernetes namespace created for the central hub."
  value       = kubernetes_namespace.central_hub.metadata[0].name
}

output "iam_role_arn" {
  description = "IAM role ARN granted to the hub's Kubernetes service account via IRSA."
  value       = aws_iam_role.central_hub.arn
}

output "entity_resolution_service" {
  description = "In-cluster DNS address of the entity resolution service."
  value       = "${kubernetes_service.entity_resolution.metadata[0].name}.${var.namespace}.svc.cluster.local"
}

output "client_briefing_service" {
  description = "In-cluster DNS address of the client briefing API."
  value       = "${kubernetes_service.client_briefing.metadata[0].name}.${var.namespace}.svc.cluster.local"
}

output "client_briefing_ingress_hostname" {
  description = "Hostname of the public ALB Ingress for the client briefing API.  Empty when enable_public_api = false."
  value       = var.enable_public_api && length(kubernetes_ingress_v1.client_briefing) > 0 ? kubernetes_ingress_v1.client_briefing[0].status[0].load_balancer[0].ingress[0].hostname : ""
}

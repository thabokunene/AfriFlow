# =============================================================================
# @file variables.tf
# @description Input variable declarations for the AfriFlow central_hub
#              Terraform module. Controls replica counts, image tags, network
#              references, and optional public API exposure settings.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================
#
# AfriFlow - Central Hub Module: Variable Definitions
#
# The central hub is the cross-country aggregation layer.  It consumes
# enriched signals from every country pod's output topics, runs entity
# resolution, computes cross-domain signals, and serves the client briefing
# API used by relationship managers.
#
# Variables here allow the central hub to be tuned independently of country
# pods — e.g. prod may run more entity resolution replicas than staging.
# =============================================================================

# ---------------------------------------------------------------------------
# Cluster Context
# ---------------------------------------------------------------------------

variable "eks_cluster_name" {
  description = <<-EOT
    Name of the EKS cluster hosting the central hub.  Used to scope IRSA
    trust policies and to tag resources so operators can correlate them
    with the correct cluster in the AWS console.
  EOT
  type = string
}

variable "eks_oidc_provider_arn" {
  description = <<-EOT
    ARN of the IAM OIDC provider attached to the EKS cluster.  Required
    for IRSA — allows Kubernetes service accounts to assume IAM roles
    without storing static credentials in the cluster.
  EOT
  type = string
}

variable "namespace" {
  description = <<-EOT
    Kubernetes namespace for the central hub.  Defaults to "afriflow-central".
    Override in cases where a shared cluster uses a different naming scheme.
  EOT
  type    = string
  default = "afriflow-central"
}

# ---------------------------------------------------------------------------
# Network / Connectivity
# ---------------------------------------------------------------------------

variable "vpc_id" {
  description = <<-EOT
    ID of the VPC hosting the EKS cluster.  Used when the module needs to
    create VPC-scoped resources (e.g. security groups for internal ALBs).
  EOT
  type = string
}

variable "kafka_bootstrap_servers" {
  description = <<-EOT
    MSK broker addresses (TLS port 9094) for the central Kafka cluster.
    The hub consumes from country pod output topics and produces to
    cross-domain signal topics via these brokers.
  EOT
  type = string
}

variable "rds_endpoint" {
  description = <<-EOT
    Hostname:port of the RDS PostgreSQL instance used for entity resolution
    state and client briefing metadata.
    Example: "afriflow-metadata-db.cxyz.af-south-1.rds.amazonaws.com:5432"
  EOT
  type = string
}

variable "rds_database_name" {
  description = "Name of the PostgreSQL database inside the RDS instance."
  type        = string
  default     = "afriflow"
}

variable "rds_username" {
  description = <<-EOT
    PostgreSQL user for hub services to authenticate with RDS.
    The password is read from a Kubernetes Secret (not a Terraform variable)
    to avoid storing credentials in state files.
  EOT
  type    = string
  default = "afriflow"
}

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

variable "delta_lake_bucket" {
  description = <<-EOT
    Name of the S3 bucket holding the Delta Lake.  The central hub reads
    Silver- and Gold-layer tables from this bucket and writes computed
    cross-domain signal tables back to it.
  EOT
  type = string
}

variable "hub_s3_prefix" {
  description = <<-EOT
    S3 key prefix under which the central hub writes its outputs.
    Defaults to "gold/central".  The hub never writes to country-pod
    Bronze prefixes; it only reads from them after country pods promote
    data to Silver.
  EOT
  type    = string
  default = "gold/central"
}

# ---------------------------------------------------------------------------
# Service Replicas
# ---------------------------------------------------------------------------

variable "entity_resolution_replicas" {
  description = <<-EOT
    Number of entity resolution service replicas.  Entity resolution is
    CPU-intensive (fuzzy matching + ML scoring) so prod should run at
    least 3 replicas behind a LoadBalancer for redundancy.
  EOT
  type    = number
  default = 2
}

variable "cross_domain_signal_replicas" {
  description = <<-EOT
    Number of replicas for the cross-domain signal processor.  This service
    joins events across forex, PBB, insurance, and cell domains to detect
    composite signals (e.g. expansion events).
  EOT
  type    = number
  default = 2
}

variable "client_briefing_replicas" {
  description = <<-EOT
    Number of replicas for the client briefing REST API.  Relationship
    managers call this API in real time, so availability is critical in prod.
    Use at least 2 replicas to allow rolling deploys without downtime.
  EOT
  type    = number
  default = 1
}

# ---------------------------------------------------------------------------
# Container Images
# ---------------------------------------------------------------------------

variable "hub_image_registry" {
  description = <<-EOT
    Base ECR registry URL (without trailing slash) for all hub service images.
    Example: "123456789012.dkr.ecr.af-south-1.amazonaws.com"
  EOT
  type    = string
  default = "public.ecr.aws/afriflow"
}

variable "hub_image_tag" {
  description = <<-EOT
    Docker image tag deployed to all hub services in this environment.
    Using a single tag per deploy ensures all services stay in sync.
    In prod use an immutable SHA tag rather than "latest".
  EOT
  type    = string
  default = "latest"
}

# ---------------------------------------------------------------------------
# Ingress / Exposure
# ---------------------------------------------------------------------------

variable "enable_public_api" {
  description = <<-EOT
    When true, the client briefing API is exposed via an Internet-facing
    AWS Application Load Balancer.  Set to false in dev/staging to avoid
    unintended external access.  The ALB is provisioned by the AWS Load
    Balancer Controller installed in the cluster.
  EOT
  type    = bool
  default = false
}

variable "alb_certificate_arn" {
  description = <<-EOT
    ARN of the ACM certificate to attach to the public ALB for HTTPS
    termination.  Required when enable_public_api = true.  Leave empty
    for internal-only deployments.
  EOT
  type    = string
  default = ""
}

variable "api_domain_name" {
  description = <<-EOT
    Fully-qualified domain name for the client briefing API endpoint
    (e.g. "api.afriflow.example.com").  Used in the Kubernetes Ingress
    host rule and the ALB listener certificate SNI match.
  EOT
  type    = string
  default = ""
}

# ---------------------------------------------------------------------------
# Environment / Tagging
# ---------------------------------------------------------------------------

variable "environment" {
  description = "Deployment environment: dev, staging, or prod."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region where the cluster is deployed."
  type        = string
  default     = "af-south-1"
}

variable "aws_account_id" {
  description = "12-digit AWS account ID used in IAM ARN construction."
  type        = string
}

variable "extra_tags" {
  description = "Additional tags merged onto all taggable resources in this module."
  type        = map(string)
  default     = {}
}

# ---------------------------------------------------------------------------
# Country Pod References
# ---------------------------------------------------------------------------

variable "active_country_codes" {
  description = <<-EOT
    List of ISO 3166-1 alpha-2 country codes whose pods are currently active.
    The central hub uses this list to scope its Kafka consumer group
    subscriptions so it only reads from topics that exist.
    Example: ["ZA", "NG", "KE", "GH", "EG"]
  EOT
  type    = list(string)
  default = ["ZA", "NG", "KE"]
}

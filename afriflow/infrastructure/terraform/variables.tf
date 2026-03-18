# =============================================================================
# @file variables.tf
# @description Input variable declarations for the AfriFlow root Terraform
#              module. All concrete values are supplied via environment-
#              specific .tfvars files in the environments/ directory.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================
#
# AfriFlow Terraform — Root Module Variable Definitions
#
# All input variables for the root module are declared here.  Concrete
# values for each environment are supplied via the corresponding file in
# environments/ (dev.tfvars, staging.tfvars, prod.tfvars).
#
# Sensitive variables (e.g. db_password) must never have default values and
# must be sourced at apply time from a secrets manager or environment variable.
# =============================================================================

# ---------------------------------------------------------------------------
# AWS / Region
# ---------------------------------------------------------------------------

variable "aws_region" {
  description = <<-EOT
    AWS region to deploy all resources into.
    AfriFlow targets af-south-1 (Cape Town) as the primary region to
    minimise latency to African data sources and satisfy data-residency
    requirements.  Change only if a secondary-region DR strategy is in scope.
  EOT
  type    = string
  default = "af-south-1"
}

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

variable "environment" {
  description = <<-EOT
    Logical environment name: "dev", "staging", or "prod".
    Drives conditional logic throughout the configuration — e.g. dev uses
    a single NAT gateway to reduce cost, prod uses one per AZ for HA.
  EOT
  type    = string
  default = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------

variable "vpc_cidr" {
  description = <<-EOT
    IPv4 CIDR block for the VPC.  Each environment uses a non-overlapping
    /16 so environments can be peered in future without re-addressing:
      dev     : 10.0.0.0/16
      staging : 10.1.0.0/16
      prod    : 10.2.0.0/16
  EOT
  type    = string
  default = "10.0.0.0/16"
}

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

variable "db_password" {
  description = <<-EOT
    Password for the RDS PostgreSQL metadata database.
    SENSITIVE — never set a default value for this variable.
    Supply at apply time via:
      export TF_VAR_db_password="$(aws secretsmanager get-secret-value \
        --secret-id afriflow/<env>/rds-password \
        --query SecretString --output text)"
  EOT
  type      = string
  sensitive = true
}

# ---------------------------------------------------------------------------
# Country Pods
# ---------------------------------------------------------------------------

variable "active_country_codes" {
  description = <<-EOT
    List of ISO 3166-1 alpha-2 country codes for which country pods should
    be provisioned.  Each code generates a distinct Kubernetes namespace,
    Flink cluster, Kafka topics, and IAM role.
    Start small in dev (e.g. ["ZA", "NG"]) and expand in staging/prod.
  EOT
  type    = list(string)
  default = ["ZA", "NG"]

  validation {
    condition     = length(var.active_country_codes) > 0
    error_message = "At least one country code must be specified."
  }
}

variable "flink_task_manager_replicas" {
  description = <<-EOT
    Default number of Flink TaskManager replicas per country pod.
    Can be overridden per-country by passing a custom map to the module.
    dev: 1, staging: 2, prod: 3+
  EOT
  type    = number
  default = 1
}

variable "flink_task_slots" {
  description = <<-EOT
    Number of task slots per TaskManager.  Total pod parallelism =
    flink_task_manager_replicas × flink_task_slots.
    Keep aligned with the number of CPU cores requested per TaskManager.
  EOT
  type    = number
  default = 2
}

variable "country_pod_cpu_limit" {
  description = "CPU limit applied to each country pod's Kubernetes ResourceQuota."
  type        = string
  default     = "4"
}

variable "country_pod_memory_limit" {
  description = "Memory limit applied to each country pod's Kubernetes ResourceQuota."
  type        = string
  default     = "8Gi"
}

variable "country_pod_pod_limit" {
  description = "Maximum number of pods allowed in each country pod namespace."
  type        = number
  default     = 20
}

# ---------------------------------------------------------------------------
# Central Hub
# ---------------------------------------------------------------------------

variable "entity_resolution_replicas" {
  description = "Number of entity resolution service replicas in the central hub."
  type        = number
  default     = 1
}

variable "cross_domain_signal_replicas" {
  description = "Number of cross-domain signal processor replicas in the central hub."
  type        = number
  default     = 1
}

variable "client_briefing_replicas" {
  description = "Number of client briefing API replicas in the central hub."
  type        = number
  default     = 1
}

variable "enable_public_api" {
  description = <<-EOT
    When true, exposes the client briefing API via an Internet-facing ALB.
    Requires alb_certificate_arn and api_domain_name to be set.
    Should be false in dev to avoid unintended external access.
  EOT
  type    = bool
  default = false
}

variable "alb_certificate_arn" {
  description = "ACM certificate ARN for the public ALB HTTPS listener. Required when enable_public_api = true."
  type        = string
  default     = ""
}

variable "api_domain_name" {
  description = "FQDN for the client briefing API Ingress host rule. Required when enable_public_api = true."
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------
# Tagging
# ---------------------------------------------------------------------------

variable "extra_tags" {
  description = <<-EOT
    Additional tags merged onto every taggable resource.
    Useful for cost-allocation overrides, compliance flags, and automation
    signals (e.g. AutoShutdown = "true" for dev environments).
  EOT
  type    = map(string)
  default = {}
}

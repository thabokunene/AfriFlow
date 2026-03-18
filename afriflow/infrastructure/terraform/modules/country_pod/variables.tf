# =============================================================================
# @file variables.tf
# @description Input variable declarations for the AfriFlow country_pod
#              Terraform module. Each variable is annotated with validation
#              rules and detailed descriptions for future maintainers.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================
#
# AfriFlow - Country Pod Module: Variable Definitions
#
# Each country pod is an isolated Kubernetes namespace that hosts the
# stream-processing workloads (Flink jobs, Kafka consumers) and data
# simulators for a single African country (e.g. ZA, NG, KE).
#
# Variables here parameterise the module so the same code can be reused
# for every country without duplication.  The root module passes values
# via `for_each` over a map of country objects.
# =============================================================================

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

variable "country_code" {
  description = <<-EOT
    ISO 3166-1 alpha-2 country code in UPPERCASE (e.g. "ZA", "NG", "KE").
    Used as a resource-naming suffix throughout the module so resources
    belonging to different countries never collide inside the same cluster.
  EOT
  type        = string

  validation {
    condition     = can(regex("^[A-Z]{2}$", var.country_code))
    error_message = "country_code must be exactly two uppercase letters (ISO 3166-1 alpha-2)."
  }
}

variable "country_name" {
  description = <<-EOT
    Human-readable country name (e.g. "South Africa").  Used in resource
    descriptions and Kubernetes labels so operators can identify pods
    without having to decode country codes.
  EOT
  type        = string
}

variable "region_group" {
  description = <<-EOT
    African region bucket this country belongs to.  Valid values are
    "southern", "west", "east", "central", "north".  Drives scheduling
    affinity so pods from the same region land on the same node-pool
    where possible, reducing cross-AZ traffic.
  EOT
  type    = string
  default = "southern"

  validation {
    condition     = contains(["southern", "west", "east", "central", "north"], var.region_group)
    error_message = "region_group must be one of: southern, west, east, central, north."
  }
}

# ---------------------------------------------------------------------------
# Cluster / Namespace
# ---------------------------------------------------------------------------

variable "eks_cluster_name" {
  description = <<-EOT
    Name of the EKS cluster that hosts this pod.  Required so the module
    can construct the correct IRSA (IAM Roles for Service Accounts) trust
    policy referencing the cluster's OIDC issuer URL.
  EOT
  type = string
}

variable "eks_oidc_provider_arn" {
  description = <<-EOT
    ARN of the IAM OIDC identity provider associated with the EKS cluster.
    Used to build the IRSA trust relationship so Kubernetes service
    accounts can assume IAM roles without storing long-lived credentials.
    Example: "arn:aws:iam::123456789012:oidc-provider/oidc.eks.af-south-1.amazonaws.com/id/ABCDEF"
  EOT
  type = string
}

variable "namespace" {
  description = <<-EOT
    Kubernetes namespace to create for this country pod.  Defaults to
    "afriflow-<lowercase country_code>" but can be overridden in
    environments where namespace naming conventions differ.
  EOT
  type    = string
  default = ""  # If empty, the module computes "afriflow-<lower(country_code)>"
}

# ---------------------------------------------------------------------------
# Kafka / Streaming
# ---------------------------------------------------------------------------

variable "kafka_bootstrap_servers" {
  description = <<-EOT
    Comma-separated list of MSK broker bootstrap addresses (TLS port 9094).
    Passed directly into Flink job ConfigMaps and simulator environment
    variables.  Example:
    "b-1.afriflow.abc123.kafka.af-south-1.amazonaws.com:9094,b-2..."
  EOT
  type = string
}

variable "kafka_topics" {
  description = <<-EOT
    Map of logical topic names to their configurations.  The module creates
    one MSK topic per entry.  Keys are short identifiers (e.g. "forex",
    "pbb", "insurance", "cell"); values are objects with:
      - partitions    : number of partitions (drives parallelism)
      - replication   : replication factor (>= 3 for prod)
      - retention_ms  : log retention in milliseconds (-1 = infinite)
  EOT
  type = map(object({
    partitions   = number
    replication  = number
    retention_ms = number
  }))

  default = {
    forex = {
      partitions   = 6
      replication  = 3
      retention_ms = 604800000   # 7 days
    }
    pbb = {
      partitions   = 12
      replication  = 3
      retention_ms = 604800000
    }
    insurance = {
      partitions   = 6
      replication  = 3
      retention_ms = 604800000
    }
    cell = {
      partitions   = 12
      replication  = 3
      retention_ms = 604800000
    }
  }
}

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

variable "delta_lake_bucket" {
  description = <<-EOT
    Name of the S3 bucket that holds the Delta Lake data.  Country pods
    write raw (bronze) events to a prefix scoped to their country code:
    s3://<bucket>/bronze/<country_code>/<domain>/
    The bucket itself is managed in the root module; this variable is a
    reference only so the pod's IAM role can be granted write access.
  EOT
  type = string
}

variable "s3_key_prefix" {
  description = <<-EOT
    Override the default S3 key prefix for this country's data.
    Defaults to "bronze/<lowercase_country_code>" if left empty.
    Useful when migrating a country between storage layouts.
  EOT
  type    = string
  default = ""
}

# ---------------------------------------------------------------------------
# Flink Processing
# ---------------------------------------------------------------------------

variable "flink_image" {
  description = <<-EOT
    Docker image (including tag) for the AfriFlow Flink job container.
    Should be an ECR image URI so EKS nodes can pull without public
    internet access.  Example:
    "123456789012.dkr.ecr.af-south-1.amazonaws.com/afriflow-flink:1.18.0"
  EOT
  type    = string
  default = "apache/flink:1.18.0-scala_2.12"
}

variable "flink_task_manager_replicas" {
  description = <<-EOT
    Number of Flink TaskManager pods per country pod.  Each TaskManager
    provides parallelism slots for stream-processing operators.
    - dev     : 1 (minimal cost)
    - staging : 2
    - prod    : 3+  (set higher for countries with large transaction volumes)
  EOT
  type    = number
  default = 1
}

variable "flink_task_slots" {
  description = <<-EOT
    Number of task slots per TaskManager pod.  Total parallelism =
    flink_task_manager_replicas × flink_task_slots.
    Keep this ≤ (CPU cores allocated to TaskManager) to avoid slot contention.
  EOT
  type    = number
  default = 2
}

# ---------------------------------------------------------------------------
# Resource Limits
# ---------------------------------------------------------------------------

variable "resource_limits" {
  description = <<-EOT
    CPU and memory hard limits applied to the Kubernetes ResourceQuota for
    this country's namespace.  Prevents a runaway country pod from starving
    other workloads on the cluster.

    Fields:
      - cpu_limit     : total CPU cores the namespace may consume
      - memory_limit  : total RAM (e.g. "8Gi") the namespace may consume
      - pod_limit     : maximum number of pods in the namespace
  EOT
  type = object({
    cpu_limit    = string
    memory_limit = string
    pod_limit    = number
  })

  default = {
    cpu_limit    = "4"
    memory_limit = "8Gi"
    pod_limit    = 20
  }
}

# ---------------------------------------------------------------------------
# Environment Context
# ---------------------------------------------------------------------------

variable "environment" {
  description = <<-EOT
    Deployment environment: "dev", "staging", or "prod".
    Controls resource sizing defaults and enables/disables optional
    features like HPA and PodDisruptionBudgets.
  EOT
  type    = string
  default = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region where the cluster resides.  Used to build IAM ARNs."
  type        = string
  default     = "af-south-1"
}

variable "aws_account_id" {
  description = <<-EOT
    12-digit AWS account ID.  Required when constructing IAM role ARNs and
    S3 bucket policy conditions programmatically inside the module.
  EOT
  type = string
}

# ---------------------------------------------------------------------------
# Tagging
# ---------------------------------------------------------------------------

variable "extra_tags" {
  description = <<-EOT
    Additional key-value tags to apply to all taggable AWS resources created
    by this module.  Merged with the module's own mandatory tags.
    Useful for cost-allocation overrides at the country level.
  EOT
  type    = map(string)
  default = {}
}

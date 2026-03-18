# =============================================================================
# @file prod.tfvars
# @description Production environment variable overrides for the AfriFlow
#              Terraform root module. Full HA configuration across 10 African
#              markets with POPIA/GDPR/NDPR compliance tagging and 3 replicas
#              per service.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================
#
# AfriFlow Terraform — Production Environment Variable Overrides
#
# PURPOSE
# -------
# Production configuration for the AfriFlow platform.  All settings here
# prioritise availability, durability, and security over cost optimisation.
#
# USAGE
# -----
#   terraform workspace select prod
#   terraform plan  -var-file=environments/prod.tfvars -out=prod.tfplan
#   terraform apply prod.tfplan
#
# CHANGE MANAGEMENT
# -----------------
# All changes to this file MUST go through a pull request and receive
# approval from at least two senior engineers before terraform apply.
# Resource changes that cause replacement (destroy + create) must be
# scheduled during an approved maintenance window.
#
# CREDENTIAL MANAGEMENT
# ---------------------
# db_password is sourced from AWS Secrets Manager at apply time:
#
#   export TF_VAR_db_password="$(aws secretsmanager get-secret-value \
#     --secret-id afriflow/prod/rds-password \
#     --query SecretString \
#     --output text \
#     --region af-south-1)"
#
# Never store the production password in this file or in version control.
#
# BLAST RADIUS WARNING
# --------------------
# terraform destroy on the prod workspace will permanently delete the MSK
# cluster and all its data.  The S3 Delta Lake bucket has versioning enabled
# and a deletion protection lifecycle policy, but always take a manual
# snapshot before any destructive operation.
# =============================================================================

# ---------------------------------------------------------------------------
# Core Settings
# ---------------------------------------------------------------------------

aws_region  = "af-south-1"
environment = "prod"

# Production VPC uses a distinct CIDR to allow future VPC peering with
# on-premises networks or partner VPCs without address overlap.
vpc_cidr = "10.2.0.0/16"

# ---------------------------------------------------------------------------
# Country Pods — Active Countries in Production
# ---------------------------------------------------------------------------

# Full set of supported markets.  Each entry creates a country pod with
# dedicated Kafka topics, a Flink cluster, and scoped S3 access.
# Onboard new countries via a PR that adds to this list.
active_country_codes = [
  "ZA",  # South Africa       — anchor market, highest event volume
  "NG",  # Nigeria            — second-largest market by transaction count
  "KE",  # Kenya              — M-Pesa integration, high mobile-money volume
  "GH",  # Ghana              — West Africa hub
  "EG",  # Egypt              — North Africa hub
  "TZ",  # Tanzania           — East Africa expansion
  "UG",  # Uganda             — East Africa expansion
  "ZM",  # Zambia             — Southern Africa
  "MZ",  # Mozambique         — Southern Africa
  "BW",  # Botswana           — Southern Africa
]

# ---------------------------------------------------------------------------
# Country Pod Sizing
#
# Prod pods run 3 Flink TaskManagers per country with 4 task slots each,
# giving 12 parallel operator slots per domain — sufficient for the
# expected transaction throughput across all active markets.
# ---------------------------------------------------------------------------

flink_task_manager_replicas = 3
flink_task_slots            = 4   # Total parallelism per country: 12

# Resource quota per country namespace — sized for peak month-end loads
country_pod_cpu_limit    = "16"
country_pod_memory_limit = "32Gi"
country_pod_pod_limit    = 50

# ---------------------------------------------------------------------------
# Central Hub
#
# Entity resolution scales aggressively in prod because relationship managers
# run bulk lookups during business hours across the entire client book.
# ---------------------------------------------------------------------------

entity_resolution_replicas   = 3
cross_domain_signal_replicas = 3
client_briefing_replicas     = 3

# Public API is live in production behind an HTTPS ALB
enable_public_api = true

# Production domain — must have a valid Route 53 record pointing to the ALB
api_domain_name = "api.afriflow.example.com"

# Production ACM certificate (must cover api.afriflow.example.com)
# Replace with the actual certificate ARN after issuance
alb_certificate_arn = "arn:aws:acm:af-south-1:123456789012:certificate/prod-cert-placeholder"

# ---------------------------------------------------------------------------
# MSK (Kafka)
#
# Prod runs 6 broker nodes on kafka.m5.xlarge for higher throughput and
# fault tolerance (2 broker failures tolerated with replication-factor 3
# and min.insync.replicas 2).
# Broker count and instance type are controlled by environment conditionals
# in the MSK resource block in main.tf.
# ---------------------------------------------------------------------------

# 6 brokers, kafka.m5.xlarge, 1 TB EBS per broker
# Topic default partitions: 12 (allows 12 parallel consumers per topic)
# min.insync.replicas: 2 (ensures durability under single-broker failure)

# ---------------------------------------------------------------------------
# RDS
#
# Multi-AZ enabled (automatic via environment != "dev" check in main.tf).
# db.r5.large: memory-optimised for the entity resolution JOIN queries
# that scan large portions of the client golden-record table.
# Backup retention: 30 days — satisfies typical regulatory requirements.
# Performance Insights and Enhanced Monitoring enabled.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CloudWatch Log Retention
# ---------------------------------------------------------------------------

# VPC Flow Logs: 90 days (security incident investigation window)
# MSK Broker Logs: 30 days (operational troubleshooting)
# Application logs: managed by the Kubernetes logging stack (Fluentd → S3),
# not directly via this Terraform config.

# ---------------------------------------------------------------------------
# KMS Key Policy
#
# All three KMS keys (MSK, RDS, S3) have automatic annual key rotation
# enabled.  Key deletion window is 30 days to allow recovery if a key is
# accidentally scheduled for deletion.
# These settings are hardcoded in the KMS resource blocks in main.tf and
# are not variable-driven — they should never be relaxed.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tagging Overrides
# ---------------------------------------------------------------------------

extra_tags = {
  CostCentre      = "engineering-prod"
  DataClass       = "confidential"      # Drives S3 bucket policy enforcement
  Compliance      = "POPIA,GDPR,NDPR"  # Regulatory frameworks in scope
  BackupRequired  = "true"
  AutoShutdown    = "false"
  SLA             = "99.9"             # Uptime SLA as a percentage
}

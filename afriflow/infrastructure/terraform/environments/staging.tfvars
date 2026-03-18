# =============================================================================
# @file staging.tfvars
# @description Staging environment variable overrides for the AfriFlow
#              Terraform root module. Near-production sizing with 4 active
#              countries, 2 replicas per service, and a staging-domain
#              public ALB for QA access.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================
#
# AfriFlow Terraform — Staging Environment Variable Overrides
#
# PURPOSE
# -------
# Staging is the pre-production validation environment.  It mirrors production
# architecture closely enough to catch configuration drift, capacity planning
# errors, and integration failures — but at reduced cost (smaller instances,
# fewer replicas, shorter log retention).
#
# USAGE
# -----
#   terraform workspace select staging
#   terraform plan  -var-file=environments/staging.tfvars
#   terraform apply -var-file=environments/staging.tfvars
#
# KEY DIFFERENCES FROM PROD
# -------------------------
# * Instance sizes are one tier smaller (m5.large vs m5.xlarge).
# * EKS node groups run 2 desired nodes instead of 3.
# * MSK has 3 brokers (vs 6 in prod) — same replication, less throughput.
# * RDS is single-AZ (vs multi-AZ in prod) — reduces cost at the expense
#   of failover capability.
# * Log retention is 30 days (vs 90 in prod).
# * Public API is enabled with a staging-specific domain name.
#
# SECURITY NOTE
# -------------
# db_password must be supplied at apply time — do not commit credentials:
#   export TF_VAR_db_password="$(aws secretsmanager get-secret-value \
#     --secret-id afriflow/staging/rds-password --query SecretString --output text)"
# =============================================================================

# ---------------------------------------------------------------------------
# Core Settings
# ---------------------------------------------------------------------------

aws_region  = "af-south-1"
environment = "staging"
vpc_cidr    = "10.1.0.0/16"   # Separate CIDR from dev (10.0.x) and prod (10.2.x)

# ---------------------------------------------------------------------------
# Country Pods — Active Countries in Staging
# ---------------------------------------------------------------------------

# Staging validates the four highest-priority markets before prod rollout.
# Additional countries are onboarded to staging before being enabled in prod.
active_country_codes = ["ZA", "NG", "KE", "GH"]

# ---------------------------------------------------------------------------
# Country Pod Sizing
# ---------------------------------------------------------------------------

# Each country pod runs 2 Flink TaskManagers in staging so parallelism
# behaviour is testable (single-TaskManager dev config hides certain race
# conditions in stateful operators).
flink_task_manager_replicas = 2
flink_task_slots            = 2   # Total parallelism per country: 4

# ---------------------------------------------------------------------------
# Central Hub
# ---------------------------------------------------------------------------

# Two replicas of stateless services provides basic redundancy and allows
# rolling deploys without downtime — mirrors the prod deployment pattern.
entity_resolution_replicas   = 2
cross_domain_signal_replicas = 2
client_briefing_replicas     = 2

# Expose the briefing API publicly so QA engineers can call it directly
# without kubectl access.
enable_public_api = true

# Staging domain — should resolve to the staging ALB via Route 53
api_domain_name = "api-staging.afriflow.internal"

# Staging ACM certificate ARN (replace with actual ARN after cert issuance)
alb_certificate_arn = "arn:aws:acm:af-south-1:123456789012:certificate/staging-cert-placeholder"

# ---------------------------------------------------------------------------
# Resource Limits per Country Pod
# ---------------------------------------------------------------------------

# Slightly more headroom than dev — enough to run realistic load tests
country_pod_cpu_limit    = "8"
country_pod_memory_limit = "16Gi"
country_pod_pod_limit    = 30

# ---------------------------------------------------------------------------
# CloudWatch Log Retention
# ---------------------------------------------------------------------------

# 30 days in staging — enough history for post-incident analysis without
# incurring the storage cost of the 90-day prod retention.
# Controlled by environment conditionals in the resource blocks.

# ---------------------------------------------------------------------------
# Tagging Overrides
# ---------------------------------------------------------------------------

extra_tags = {
  CostCentre   = "engineering-staging"
  AutoShutdown = "false"   # Staging stays up 24/7 for integration test suites
  Ephemeral    = "false"
}

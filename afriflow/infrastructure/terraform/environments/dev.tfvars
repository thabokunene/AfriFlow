# =============================================================================
# @file dev.tfvars
# @description Development environment variable overrides for the AfriFlow
#              Terraform root module. Cost-optimised settings with minimal
#              replicas, shortest log retention, and no public API exposure.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================
#
# AfriFlow Terraform — Development Environment Variable Overrides
#
# PURPOSE
# -------
# This file supplies concrete values for every variable declared in
# variables.tf that differs from the production defaults.  It is passed to
# Terraform with:
#
#   terraform plan  -var-file=environments/dev.tfvars
#   terraform apply -var-file=environments/dev.tfvars
#
# PHILOSOPHY
# ----------
# * Cost-optimised  : smallest viable instance types, single NAT gateway.
# * Speed-optimised : shorter retention, smaller node groups so apply/destroy
#                     cycles complete quickly for developer iteration.
# * NOT production-like: do not use this file to benchmark performance or
#   validate HA behaviour.
#
# SECURITY NOTE
# -------------
# The db_password variable is intentionally absent from this file.
# Supply it at apply time via an environment variable:
#   export TF_VAR_db_password="dev-only-password-change-before-prod"
# or via a local terraform.tfvars that is .gitignored.
# =============================================================================

# ---------------------------------------------------------------------------
# Core Settings
# ---------------------------------------------------------------------------

# Target the Cape Town (af-south-1) region so latency to African data
# sources is minimised.  This matches prod; do NOT change for dev.
aws_region = "af-south-1"

# Environment label stamped on every resource tag.  Used by cost-allocation
# reports to separate dev spend from staging and prod.
environment = "dev"

# CIDR block for the dev VPC.  Uses the same /16 as prod so networking
# module code is identical; the separate VPC prevents routing overlap.
vpc_cidr = "10.0.0.0/16"

# ---------------------------------------------------------------------------
# EKS Node Groups
#
# Dev uses burstable instances (t3) rather than the m5/c5 instances used
# in staging/prod.  This reduces idle cost significantly for a cluster that
# may sit unused overnight.
#
# NOTE: The instance types below are illustrative — they are controlled
# inside the eks module block in main.tf, not directly via these vars.
# These comments document intent for the human reviewer.
# ---------------------------------------------------------------------------

# Dev cluster: 1 node per group is enough for functional testing
# country-pods : 1× t3.xlarge  (2 CPU, 16 GB RAM)
# central-hub  : 1× t3.large   (2 CPU, 8 GB RAM)
# streaming    : 1× t3.large

# ---------------------------------------------------------------------------
# MSK (Kafka)
# ---------------------------------------------------------------------------

# 3 broker nodes (minimum for replication-factor 3) on kafka.t3.small
# Dev retention is 24 hours to avoid storage costs on idle topics
# These settings are set inline in the MSK resource in main.tf, controlled
# by environment conditionals — no additional var needed.

# ---------------------------------------------------------------------------
# RDS
# ---------------------------------------------------------------------------

# db.t3.medium in dev — smallest instance that comfortably runs Postgres 15
# Multi-AZ is disabled in dev (controlled by environment == "dev" check)
# Backup retention: 7 days (minimum, to enable point-in-time recovery testing)

# ---------------------------------------------------------------------------
# Country Pods — Active Countries in Dev
# ---------------------------------------------------------------------------

# In development, only South Africa and Nigeria are active.  This limits
# Kafka topic count, S3 prefixes, and Flink job count during local testing.
active_country_codes = ["ZA", "NG"]

# ---------------------------------------------------------------------------
# Central Hub
# ---------------------------------------------------------------------------

# Only 1 replica of each hub service in dev — no HA required
entity_resolution_replicas   = 1
cross_domain_signal_replicas = 1
client_briefing_replicas     = 1

# Do not expose the API publicly in dev — use kubectl port-forward instead
enable_public_api = false

# ---------------------------------------------------------------------------
# CloudWatch Log Retention
# ---------------------------------------------------------------------------

# Short retention reduces CloudWatch storage cost in dev.
# Overridden in staging (30 days) and prod (90 days).
# Controlled by environment conditionals in main.tf resource blocks.

# ---------------------------------------------------------------------------
# Tagging Overrides
# ---------------------------------------------------------------------------

# Additional cost-allocation tags applied to all resources in this environment
extra_tags = {
  CostCentre  = "engineering-dev"
  AutoShutdown = "true"   # Signal for a Lambda scheduler to stop EC2/RDS overnight
}

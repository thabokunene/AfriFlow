# =============================================================================
# @file main.tf
# @description Root Terraform configuration for the AfriFlow platform on AWS.
#              Provisions VPC, EKS cluster, MSK (Kafka), RDS (PostgreSQL),
#              S3 Delta Lake buckets, KMS keys, CloudWatch log groups,
#              IAM roles, and security groups.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================
#
# DISCLAIMER: This project is not a sanctioned initiative
# of Standard Bank Group, MTN, or any affiliated entity.
# It is a demonstration of concept, domain knowledge,
# and data engineering skill by Thabo Kunene.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }

  backend "s3" {
    bucket = "afriflow-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "af-south-1"

    encrypt        = true
    dynamodb_table = "afriflow-terraform-locks"
  }
}

# =============================================================================
# PROVIDER CONFIGURATION
# =============================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AfriFlow"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "data-engineering"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args = [
      "eks",
      "get-token",
      "--cluster-name",
      module.eks.cluster_name
    ]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args = [
        "eks",
        "get-token",
        "--cluster-name",
        module.eks.cluster_name
      ]
    }
  }
}

# =============================================================================
# VPC & NETWORKING
# =============================================================================

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "afriflow-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment == "dev"
  one_nat_gateway_per_az = var.environment != "dev"

  enable_dns_hostnames = true
  enable_dns_support   = true

  # VPC Flow Logs for security monitoring
  enable_flow_log                      = true
  vpc_flow_log_cloudwatch_iam_role_arn = aws_iam_role.flow_logs.arn
  vpc_flow_log_cloudwatch_log_group_name = aws_cloudwatch_log_group.flow_logs.name

  tags = {
    Name = "afriflow-vpc"
  }
}

# =============================================================================
# EKS CLUSTER
# =============================================================================

module "eks" {
  source = "terraform-aws-modules/eks/aws"

  cluster_name    = "afriflow-cluster"
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Control plane logging
  cluster_endpoint_public_access  = var.environment == "dev"
  cluster_endpoint_private_access = true

  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    # Country pod node groups (created dynamically per country)
    country-pods = {
      name = "country-pods"

      instance_types = ["m5.2xlarge"]

      min_size     = 3
      max_size     = 20
      desired_size = 5

      # Taint for country pod workloads
      taints = {
        country-pod = {
          key    = "workload"
          value  = "country-pod"
          effect = "NO_SCHEDULE"
        }
      }

      labels = {
        "afriflow/node-type" = "country-pod"
      }
    }

    # Central hub node group
    central-hub = {
      name = "central-hub"

      instance_types = ["m5.4xlarge"]

      min_size     = 2
      max_size     = 10
      desired_size = 3

      labels = {
        "afriflow/node-type" = "central-hub"
      }
    }

    # Streaming node group
    streaming = {
      name = "streaming"

      instance_types = ["c5.2xlarge"]

      min_size     = 2
      max_size     = 10
      desired_size = 3

      labels = {
        "afriflow/node-type" = "streaming"
      }
    }
  }

  # EKS add-ons
  cluster_addons = {
    coredns = {
      resolve_conflicts_on_update = "OVERWRITE"
    }
    kube-proxy = {
      resolve_conflicts_on_update = "OVERWRITE"
    }
    vpc-cni = {
      resolve_conflicts_on_update = "OVERWRITE"
    }
    aws-ebs-csi-driver = {
      resolve_conflicts_on_update = "OVERWRITE"
    }
  }

  tags = {
    "afriflow/cluster" = "true"
  }
}

# =============================================================================
# MSK (Managed Kafka)
# =============================================================================

resource "aws_msk_cluster" "afriflow_msk" {
  cluster_name           = "afriflow-msk"
  kafka_version          = "3.5.1"
  number_of_broker_nodes = var.environment == "dev" ? 3 : 6

  broker_node_group_info {
    instance_type   = var.environment == "dev" ? "kafka.m5.large" : "kafka.m5.xlarge"
    ebs_volume_size = 1000
    client_subnets  = module.vpc.private_subnets
    security_groups = [aws_security_group.msk.id]
  }

  encryption_info {
    encryption_at_rest_kms_key_id = aws_kms_key.msk.arn

    encryption_in_transit_kms_key_id = aws_kms_key.msk.arn
    client_broker                    = "TLS"
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk_broker_logs.name
      }

      s3 {
        enabled = true
        bucket  = aws_s3_bucket.msk_logs.id
        prefix  = "msk-broker-logs/"
      }
    }
  }

  tags = {
    Name = "afriflow-msk"
  }
}

# =============================================================================
# RDS — Subnet Group
#
# The DB subnet group tells RDS which private subnets it may place the
# primary and standby instances in.  Using all three private subnets ensures
# Multi-AZ deployments can spread across every availability zone in the
# region (af-south-1a/b/c) for maximum fault isolation.
# =============================================================================

resource "aws_db_subnet_group" "afriflow" {
  name        = "afriflow-db-subnet-group"
  description = "Subnet group for AfriFlow RDS metadata database — spans all private subnets for Multi-AZ support"
  subnet_ids  = module.vpc.private_subnets

  tags = {
    Name    = "afriflow-db-subnet-group"
    Purpose = "RDS metadata database subnet placement"
  }
}

# DynamoDB table used by the Terraform S3 backend for state locking.
# This prevents concurrent terraform applies from corrupting the state file.
# Must be created before the backend is initialised; see README for bootstrap
# instructions.
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "afriflow-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"  # On-demand — lock operations are infrequent
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  # Enable point-in-time recovery so the locks table can be restored if
  # accidentally deleted alongside other resources.
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name    = "afriflow-terraform-locks"
    Purpose = "Terraform state locking — do not delete"
  }
}

# =============================================================================
# RDS (PostgreSQL for Metadata)
# =============================================================================

module "rds" {
  source = "terraform-aws-modules/rds/aws"

  identifier = "afriflow-metadata-db"

  engine            = "postgres"
  engine_version    = "15.4"
  family            = "postgres15"
  major_engine_version = "15"
  instance_class    = var.environment == "dev" ? "db.t3.medium" : "db.r5.large"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_encrypted     = true
  kms_key_id           = aws_kms_key.rds.arn

  db_name  = "afriflow"
  username = "afriflow"
  password = var.db_password
  port     = 5432

  multi_az               = var.environment != "dev"
  db_subnet_group_name   = aws_db_subnet_group.afriflow.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  maintenance_window = "Mon:00:00-Mon:03:00"

  backup_retention_period = var.environment == "dev" ? 7 : 30
  backup_window          = "03:00-06:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  parameters = [
    {
      name  = "autovacuum"
      value = 1
    },
    {
      name  = "client_encoding"
      value = "utf8"
    }
  ]

  tags = {
    Name = "afriflow-metadata-db"
  }
}

# =============================================================================
# S3 Buckets
# =============================================================================

# Delta Lake storage
resource "aws_s3_bucket" "delta_lake" {
  bucket = "afriflow-delta-lake-${var.environment}"

  tags = {
    Name = "afriflow-delta-lake"
    Purpose = "Data Lake Storage"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "delta_lake" {
  bucket = aws_s3_bucket.delta_lake.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "delta_lake" {
  bucket = aws_s3_bucket.delta_lake.bucket

  rule {
    id     = "bronze-to-silver"
    status = "Enabled"

    filter {
      prefix = "bronze/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# MSK logs
resource "aws_s3_bucket" "msk_logs" {
  bucket = "afriflow-msk-logs-${var.environment}"

  tags = {
    Name = "afriflow-msk-logs"
  }
}

# Terraform state
resource "aws_s3_bucket" "terraform_state" {
  bucket = "afriflow-terraform-state"

  tags = {
    Name = "afriflow-terraform-state"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.bucket

  versioning_configuration {
    status = "Enabled"
  }
}

# =============================================================================
# KMS Keys
# =============================================================================

resource "aws_kms_key" "msk" {
  description             = "KMS key for MSK encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "afriflow-msk-key"
  }
}

resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "afriflow-rds-key"
  }
}

resource "aws_kms_key" "s3" {
  description             = "KMS key for S3 encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "afriflow-s3-key"
  }
}

# =============================================================================
# CloudWatch
# =============================================================================

resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/aws/vpc/afriflow-flow-logs"
  retention_in_days = var.environment == "dev" ? 7 : 90
}

resource "aws_cloudwatch_log_group" "msk_broker_logs" {
  name              = "/aws/msk/afriflow-msk/broker-logs"
  retention_in_days = var.environment == "dev" ? 7 : 30
}

# =============================================================================
# IAM Roles
# =============================================================================

resource "aws_iam_role" "flow_logs" {
  name = "afriflow-vpc-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  name = "afriflow-vpc-flow-logs-policy"
  role = aws_iam_role.flow_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# =============================================================================
# SECURITY GROUPS
# =============================================================================

resource "aws_security_group" "msk" {
  name        = "afriflow-msk-sg"
  description = "Security group for MSK cluster"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Kafka from VPC"
    from_port       = 9092
    to_port         = 9092
    protocol        = "tcp"
    cidr_blocks     = [module.vpc.vpc_cidr_block]
    security_groups = [aws_security_group.eks_nodes.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }

  tags = {
    Name = "afriflow-msk-sg"
  }
}

resource "aws_security_group" "rds" {
  name        = "afriflow-rds-sg"
  description = "Security group for RDS"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL from EKS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }

  tags = {
    Name = "afriflow-rds-sg"
  }
}

resource "aws_security_group" "eks_nodes" {
  name        = "afriflow-eks-nodes-sg"
  description = "Security group for EKS nodes"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [module.eks.cluster_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }

  tags = {
    Name = "afriflow-eks-nodes-sg"
  }
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "msk_cluster_arn" {
  description = "MSK cluster ARN"
  value       = aws_msk_cluster.afriflow_msk.arn
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.db_instance_endpoint
}

output "delta_lake_bucket" {
  description = "Delta Lake S3 bucket"
  value       = aws_s3_bucket.delta_lake.bucket
}

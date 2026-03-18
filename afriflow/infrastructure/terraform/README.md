# AfriFlow Terraform Infrastructure

This directory contains the Terraform configuration for the AfriFlow platform on AWS.

## Architecture
- **VPC**: Multi-AZ networking with private and public subnets.
- **EKS**: Managed Kubernetes cluster for application workloads.
- **MSK**: Managed Kafka cluster for event streaming.
- **RDS**: Managed PostgreSQL for metadata storage.
- **S3**: Data lake storage (Delta Lake) and logging.

## Usage
1. Initialize Terraform:
   ```bash
   terraform init
   ```
2. Create a `terraform.tfvars` file with the required variables:
   ```hcl
   db_password = "your-secure-password"
   ```
3. Plan and apply:
   ```bash
   terraform plan
   ```

## Security
- MSK is encrypted in transit via TLS.
- Security groups are restricted to VPC-internal traffic where possible.
- All S3 buckets are encrypted with KMS.

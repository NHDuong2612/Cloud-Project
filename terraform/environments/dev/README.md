# CloudRescue — environment notes (dev)

This folder documents the **dev** environment. Root Terraform lives in
`terraform/` (parent of this directory).

## How we run Terraform (Phase 1+)

```powershell
cd terraform
copy terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — fill <YOUR_*> values (never commit this file)

$env:AWS_PROFILE = "cloudrescue-dev"
$env:AWS_REGION  = "<YOUR_REGION>"

terraform fmt -recursive
terraform init
terraform validate
```

## Feature flags by phase

| Phase | Flag to set `true` in `terraform.tfvars` | Creates |
|------|------------------------------------------|---------|
| 1 Skeleton | (all false) | Nothing in AWS |
| 2 Network | `enable_network` | VPC, subnets, IGW, routes |
| 3 SG + IAM | `enable_iam` | Security groups + controller role/profile |
| 4 S3 | `enable_storage` | Backup bucket |
| 5 RDS | `enable_database` | Private PostgreSQL (**costs money**) |

Controller EC2 (`enable_controller`) stays off until needed to save cost.

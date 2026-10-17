# CloudRescue — Terraform (Người 2 / AWS Infrastructure)

Infrastructure as Code for the AWS recovery side of:

**OpenStack → S3 backups → AWS recovery (Controller / Target / RDS) → Validation → Dashboard**

## What this folder is for

| Module | Responsibility | Enable flag |
|--------|----------------|-------------|
| `modules/network` | VPC, public subnet, 2 private DB subnets, IGW, routes | `enable_network` |
| `modules/iam` | Security groups + IAM role/instance profile (S3, SSM) | `enable_iam` |
| `modules/storage` | Private S3 backup bucket (SSE + versioning) | `enable_storage` |
| `modules/database` | RDS PostgreSQL Single-AZ (private) | `enable_database` |
| `modules/controller` | Controller EC2 (later; cost) | `enable_controller` |
| `modules/observability` | CloudWatch placeholders | `enable_observability` |

```
OpenStack app
    → backup objects → S3 (storage)
    → restore drill  → Controller EC2 (controller) + Target
    → application DB → RDS (database) in private subnets (network)
    → least privilege → SG + IAM (iam)
```

## Prerequisites

1. AWS CLI configured with profile `cloudrescue-dev` (or Identity Center).
2. MFA on admin; **no root access keys**.
3. Terraform **>= 1.5** installed: https://developer.hashicorp.com/terraform/install
4. Region and tags agreed in `docs/aws-convention.md`.

Check identity (must not be root access key):

```powershell
$env:AWS_PROFILE = "cloudrescue-dev"
aws sts get-caller-identity
```

## Security rules

- Never put `aws_access_key_id` / `aws_secret_access_key` in `.tf` files.
- Never commit `terraform.tfvars`, `*.tfstate`, credential CSV, or `.env`.
- DB password: use `TF_VAR_db_password` or gitignored `terraform.tfvars`.
- RDS and S3 stay private; no `0.0.0.0/0` on PostgreSQL.

## Phase 1 — Skeleton only (current)

Goal: `terraform validate` **PASS** with **zero** paid resources.

### 1. Copy tfvars

```powershell
cd terraform
copy terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and replace:

- `<YOUR_REGION>`
- `<YOUR_OWNER>`
- `<YOUR_EXPIRES_AT>`

Keep all `enable_* = false`.

### 2. Format / init / validate

```powershell
$env:AWS_PROFILE = "cloudrescue-dev"

terraform fmt -recursive
terraform init
terraform validate
```

Expected:

```text
Success! The configuration is valid.
```

### 3. Optional plan (should show no creates)

```powershell
terraform plan
```

With all flags false, modules create **no** AWS resources (outputs may be null).

## Cost warning (later phases)

| Resource | When | Cost note |
|----------|------|-----------|
| VPC / subnet / SG / IAM | Phase 2–3 | Usually free |
| S3 | Phase 4 | Pennies for demo objects |
| RDS `db.t3.micro` | Phase 5 | **Hourly** — stop/delete after demo |
| EC2 controller | Later | **Hourly** — stop when idle |
| NAT Gateway | Avoided | ~$32+/month — **not** used in this design |

## Dependency graph

```text
network (VPC, subnets)
    ├── iam (security groups need vpc_id; role for controller)
    │       └── controller (needs subnet + SG + instance profile)
    ├── database (needs private subnets + database SG)
    └── storage (S3; IAM policy references bucket ARN)
observability (optional, independent)
```

## Outputs for Người 3 (after later phases)

After apply with flags enabled, run:

```powershell
terraform output
```

Hand off: VPC ID, subnet IDs, SG IDs, bucket name/ARN, RDS endpoint (sensitive), IAM instance profile.

## Evidence (Phase 1)

| File | Proves |
|------|--------|
| `evidence/person2/01-terraform-validate.png` | `terraform validate` Success |
| `evidence/person2/01-terraform-fmt-init.png` | fmt + init completed |
| `evidence/person2/01-tree-terraform.png` | Folder structure |

## Next

After you confirm Phase 1 PASS, we implement **Phase 2 — Network** only.

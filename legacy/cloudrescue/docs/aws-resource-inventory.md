# AWS resource inventory — ARN/ID non-sensitive handoff

> AWS state checked on 2026-09-26 in `ap-southeast-1`, account
> `800591602832`. Contains resource identifiers for Người 3. This inventory
> intentionally omits the RDS endpoint, Secrets Manager ARN/value, passwords,
> access keys, and session credentials.

## Network

| Resource | Name | ID / ARN | Notes |
|----------|------|----------|-------|
| VPC | `cloudrescue-dev-vpc` | `vpc-03b63acd439d77a13` | `10.20.0.0/16` |
| Internet Gateway | `cloudrescue-dev-igw` | `igw-01178fd70436d4c5e` | Attached to VPC above |
| Public subnet | `cloudrescue-dev-subnet-public-a` | `subnet-0777e74eeda3cd848` | AZ `ap-southeast-1a`, `10.20.1.0/24` |
| Private DB subnet A | `cloudrescue-dev-subnet-db-a` | `subnet-0a76d15cfa49b98cb` | AZ `ap-southeast-1a`, `10.20.10.0/24` |
| Private DB subnet B | `cloudrescue-dev-subnet-db-b` | `subnet-0d2a1df96013327e2` | AZ `ap-southeast-1b`, `10.20.11.0/24` |
| Public route table | `cloudrescue-dev-rtb-public` | `rtb-0837f52a82cca4149` | Default route to IGW |
| Private DB route table A | `cloudrescue-dev-rtb-db-a` | `rtb-01b16fbb6234dea5d` | Local VPC route only |
| Private DB route table B | `cloudrescue-dev-rtb-db-b` | `rtb-0b6d05ccb61a22bed` | Local VPC route only |

Subnet ARNs:

- Public: `arn:aws:ec2:ap-southeast-1:800591602832:subnet/subnet-0777e74eeda3cd848`
- Private A: `arn:aws:ec2:ap-southeast-1:800591602832:subnet/subnet-0a76d15cfa49b98cb`
- Private B: `arn:aws:ec2:ap-southeast-1:800591602832:subnet/subnet-0d2a1df96013327e2`

## Security groups

| Resource | Name | ID | VPC |
|----------|------|----|-----|
| Controller SG | `cloudrescue-dev-sg-controller` | `sg-07c55761a62632daf` | `vpc-03b63acd439d77a13` |
| Target SG | `cloudrescue-dev-sg-target` | `sg-0d0e63ccd1ce83817` | `vpc-03b63acd439d77a13` |
| Database SG | `cloudrescue-dev-sg-database` | `sg-03d2ac3cac8fa3afb` | `vpc-03b63acd439d77a13` |

Database ingress is TCP 5432 from the controller and target security groups.

## Storage

| Resource | Name | ARN | Region |
|----------|------|-----|--------|
| S3 backup bucket | `cloudrescue-dev-backups-800591602832` | `arn:aws:s3:::cloudrescue-dev-backups-800591602832` | `ap-southeast-1` |

## Controller and IAM

| Resource | Name | ID / ARN | Status |
|----------|------|----------|--------|
| Controller EC2 | `cloudrescue-dev-controller` | `i-09dad9aa959760e33` | `running` |
| IAM role | `cloudrescue-dev-role-controller` | `arn:aws:iam::800591602832:role/cloudrescue-dev-role-controller` | Attached to instance profile |
| Instance profile | `cloudrescue-dev-profile-controller` | `arn:aws:iam::800591602832:instance-profile/cloudrescue-dev-profile-controller` | Attached to controller |
| SSM test command | Task 9 smoke test | `1be1ff84-fcde-45cd-84b7-3ff75647f2df` | `Success` |

## Database

| Resource | Name | ID / ARN | Status |
|----------|------|----------|--------|
| RDS PostgreSQL | `cloudrescue-dev-rds` | `arn:aws:rds:ap-southeast-1:800591602832:db:cloudrescue-dev-rds` | `available`, PostgreSQL 16.13, `db.t3.micro`, Single-AZ, private |
| RDS DB subnet group | `cloudrescue-dev-db-subnet-group` | Name only | Uses the two private DB subnets above |

The sensitive RDS endpoint is available from the sensitive Terraform output
when needed. Do not copy it or the RDS-managed secret ARN/value into this
general handoff inventory.

## Terraform outputs

For outputs not marked sensitive:

```powershell
cd terraform
terraform output
```

The endpoint/address and RDS master secret ARN outputs are marked sensitive and
are intentionally excluded from this inventory.

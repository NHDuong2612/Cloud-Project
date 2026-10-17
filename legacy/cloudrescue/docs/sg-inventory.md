# Security Group inventory (Task 6) — non-secret IDs

> Không ghi access key / password. Làm mới: `cd terraform; terraform output`

| SG | Name | ID | Gắn vào |
|----|------|-----|---------|
| Controller | `cloudrescue-dev-sg-controller` | `sg-07c55761a62632daf` | Controller EC2 `i-09dad9aa959760e33` |
| Target | `cloudrescue-dev-sg-target` | `sg-0d0e63ccd1ce83817` | Target EC2 (sau) |
| Database | `cloudrescue-dev-sg-database` | `sg-03d2ac3cac8fa3afb` | RDS (Task 8) |
| VPC | `cloudrescue-dev-vpc` | `vpc-03b63acd439d77a13` | Chung |

## Inbound (tóm tắt)

| SG | Port | Nguồn | Ý nghĩa |
|----|------|-------|---------|
| controller | TCP all | target-sg | Peer traffic restore/validate |
| controller | 22 | `ssh_ingress_cidr` (optional) | SSH operator — mặc định **tắt** |
| target | 22, 80, 443, 8000 | controller-sg | Chỉ controller gọi app/SSH |
| database | **5432** | controller-sg + target-sg | PostgreSQL — **không** `0.0.0.0/0` |

## Outbound

Cả 3 SG: egress all (controller/target cần S3/SSM/HTTPS; RDS managed).

## RDS không public — chứng minh kép

1. **SG:** 5432 chỉ từ controller/target SG (Task 6 — đã xong).
2. **Subnet private** (Task 5) + `publicly_accessible = false` (Task 8).

## IAM role / instance profile (Task 9)

| Thành phần | Tên / ARN |
|------------|-----------|
| Role | `cloudrescue-dev-role-controller` |
| Instance profile | `cloudrescue-dev-profile-controller` |
| Attached managed policy | `AmazonSSMManagedInstanceCore` |

Controller profile và SSM Run Command đã được xác minh; chi tiết xem `docs/controller-ssm-inventory.md`.

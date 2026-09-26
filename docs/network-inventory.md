# Network inventory (Task 5) — non-secret IDs for Người 3

> Không ghi access key / password. Làm mới: `cd terraform; terraform output`

| Resource | Name | ID / Value |
|----------|------|------------|
| Region | — | `ap-southeast-1` |
| VPC | `cloudrescue-dev-vpc` | `vpc-03b63acd439d77a13` |
| IGW | `cloudrescue-dev-igw` | `igw-01178fd70436d4c5e` |
| Public subnet | `cloudrescue-dev-subnet-public-a` | `subnet-0777e74eeda3cd848` (AZ `ap-southeast-1a`) |
| Private DB subnet A | `cloudrescue-dev-subnet-db-a` | `subnet-0a76d15cfa49b98cb` (AZ `ap-southeast-1a`) |
| Private DB subnet B | `cloudrescue-dev-subnet-db-b` | `subnet-0d2a1df96013327e2` (AZ `ap-southeast-1b`) |
| VPC CIDR | — | `10.20.0.0/16` |
| Public CIDR | — | `10.20.1.0/24` |
| Private DB CIDRs | — | `10.20.10.0/24`, `10.20.11.0/24` |
| NAT Gateway | — | **Không tạo** (tiết kiệm chi phí) |

Security Groups: xem `docs/sg-inventory.md` (Task 6).


## Thiết kế

```text
cloudrescue-dev-vpc (10.20.0.0/16)
├── Public  AZ-a  10.20.1.0/24   → controller + target (sau)
├── Private AZ-a  10.20.10.0/24  → RDS subnet group
└── Private AZ-b  10.20.11.0/24  → RDS subnet group
```

- Public RTB: `0.0.0.0/0` → IGW  
- Private RTB: chỉ local VPC (RDS không ra Internet)

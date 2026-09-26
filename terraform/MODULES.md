# Terraform modules — dependency map (Task 4)

```text
                    ┌─────────────────┐
                    │  observability  │  (optional)
                    └─────────────────┘

┌──────────┐     ┌──────────┐     ┌────────────┐
│ network  │────▶│   iam    │────▶│ controller │
│ VPC/sub  │     │ SG+Role  │     │ EC2+SSM    │
└────┬─────┘     └────▲─────┘     └────────────┘
     │                │
     │                │ bucket ARN
     │           ┌────┴─────┐
     │           │ storage  │  S3 backups (OpenStack → AWS)
     │           └──────────┘
     │
     └──────────▶┌──────────┐
                 │ database │  RDS PostgreSQL (private)
                 └──────────┘
```

## Mapping OpenStack → AWS

| Thành phần hệ thống | Module Terraform |
|---------------------|------------------|
| Nơi nhận backup từ OpenStack | `storage` (S3) |
| Mạng recovery | `network` |
| Quyền & tường lửa | `iam` |
| DB sau restore | `database` |
| Máy điều phối restore/validate | `controller` |
| Log / theo dõi job | `observability` |

## Feature flags (tiết kiệm chi phí)

Tất cả mặc định `false` ở Task 4 → **không tạo resource AWS trả phí**.

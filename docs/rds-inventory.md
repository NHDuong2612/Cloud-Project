# RDS inventory (Task 8) — không chứa secret

> Xác minh trực tiếp trên AWS ngày 2026-09-26 tại region `ap-southeast-1`.
> Không lưu master password hoặc nội dung Secrets Manager trong tài liệu này.

## Cấu hình RDS

| Thuộc tính | Giá trị |
|------------|---------|
| DB identifier | `cloudrescue-dev-rds` |
| Engine | PostgreSQL `16.13` |
| Instance class | `db.t3.micro` |
| Availability | Single-AZ (`MultiAZ = false`) |
| AZ | `ap-southeast-1a` |
| Public access | **Tắt** (`PubliclyAccessible = false`) |
| Storage encryption | **Bật** |
| Port | `5432` |
| VPC | `vpc-03b63acd439d77a13` |
| DB subnet group | `cloudrescue-dev-db-subnet-group` |
| Database SG | `sg-03d2ac3cac8fa3afb` |

Private endpoint được giữ trong Terraform sensitive output và không ghi vào inventory này.

## Kiểm thử từ controller

| Thuộc tính | Giá trị |
|------------|---------|
| Controller instance | `i-09dad9aa959760e33` |
| Controller private IP | `10.20.1.15` |
| Controller SG | `sg-07c55761a62632daf` |
| SSM status lúc kiểm thử | `Online` |
| SSM command ID thành công | `eeceec25-f226-4bf8-844e-f9b6aa7f138b` |
| DNS endpoint | Phân giải thành private IP `10.20.10.125` |
| TCP 5432 | `CONNECTED` |
| PostgreSQL query | PASS — database `cloudrescue`, PostgreSQL `16.13` |
| TLS | Bắt buộc trong chuỗi kết nối (`sslmode=require`) |

Kết quả này chứng minh controller EC2 kết nối end-to-end tới RDS bằng private endpoint trong VPC; không đi qua public Internet và không mở PostgreSQL ra `0.0.0.0/0`.

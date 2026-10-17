# AWS Resource Tagging Convention

| Tag Key | Value ví dụ / Giá trị thực tế | Bắt buộc? | Ghi chú |
| :--- | :--- | :--- | :--- |
| `Project` | `CloudRescue` | Có | Đúng chính tả/casing |
| `Environment` | `dev` | Có | Môi trường phát triển |
| `Owner` | `nhom01-person2` | Có | Điền tên/mã cá nhân hoặc nhóm của bạn |
| `JobId` | `none` | Có | Để `none` cho tài nguyên chung / Budget |
| `Mode` | `shared` | Có | Chế độ dùng chung |
| `ExpiresAt` | `2026-12-31` | Có | Ngày hết hạn tài nguyên tạm thời |
| `ManagedBy` | `terraform` | Khuyến nghị | Dùng `terraform` từ Task 4 (IaC) trở đi |
| Admin Console User | `cloudrescue-admin` | Có | IAM user làm việc hàng ngày |
| CLI profile name | `cloudrescue-dev` | Có | `AWS_PROFILE` trên máy local |
| Region (đề xuất) | `ap-southeast-1` | Có | Phải thống nhất cả nhóm |
| Naming pattern | `cloudrescue-dev-{resource}` | Có | VD: `cloudrescue-dev-vpc` |
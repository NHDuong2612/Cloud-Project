# A03 — kết quả ngày 17/10/2026

Bản này là kết quả trước triển khai; xem [minh chứng apply thành công ngày 19/10/2026](foundation-applied.md) để có trạng thái hiện tại.

- Terraform init và validate: đạt, AWS provider 5.100.0.
- Ba kiểm thử preflight: đạt (chặn nhầm account, chặn root, yêu cầu hai AZ).
- AWS STS xác nhận account của nhóm bằng profile cũ; không in credential.
- Region: ap-southeast-1. Service Quotas trả giới hạn EC2 standard 8 vCPU, RDS 40 DB instances, Fargate On-Demand 8 vCPU. Đây không phải số tài nguyên còn trống.
- Chưa chạy Terraform apply; chưa kiểm chứng quyền tạo tài nguyên thực tế. T04/T06 đang chờ domain/Route53/ACM và image ECR được duyệt (nhóm xác nhận chưa có).

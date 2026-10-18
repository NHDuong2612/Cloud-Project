# Kế hoạch nền tảng — 19/10/2026

Plan đã chạy bằng profile IAM cloudrescue-dev trong ap-southeast-1, chặn account khác bằng allowed_account_ids. Kết quả: **33 add, 0 change, 0 destroy** (32 AWS resource/configuration và một terraform_data).

- Network: một VPC, một Internet Gateway, bốn subnet trong hai AZ, ba route table, bốn association và một route public. Không có NAT Gateway.
- Platform: một control table DynamoDB có PITR/stream, ECR repository, một permissions boundary, một CloudFormation role và inline policy.
- Storage: hai bucket (deployment và recovery) với cấu hình riêng tư, versioning, ownership, SSE/TLS và lifecycle abort multipart cho recovery.
- enable_orchestrator=false; plan này chưa tạo Lambda/Step Functions hoặc EC2/RDS/ALB/Fargate workload. Hai bộ artifacts app và worker đã đóng gói cục bộ, chưa upload.

Plan nhị phân lưu ở build/cloudhub-foundation.tfplan, bị gitignore; không commit state/tfvars/plan. Chưa apply tại thời điểm ghi tài liệu. Team review plan/chi phí theo terraform/terraform.tfvars.example trước bước tạo tài nguyên. Chi phí dữ liệu/request/PITR/ECR không được xem là miễn phí chỉ vì chưa có compute; chưa có dự toán F03 hay ngân sách triển khai được xác nhận.

Trước apply, kiểm tra lại identity, plan, quota và trùng tên bucket/repository. Plan là ảnh chụp thời điểm hiện tại, không bảo đảm đủ mọi quyền create hoặc dịch vụ đã provision được. Sau khi đổi cấu hình hoặc trạng thái AWS, tạo plan mới. Không dùng plan này để dọn legacy hoặc xóa nền tảng chung.

# CloudHub — phần việc TV3

CloudHub tạo và quản lý môi trường AWS theo phiên. Phần TV3 cung cấp hạ tầng dùng chung, danh mục mẫu có phiên bản và bộ điều phối CloudFormation. Mã CloudRescue và Terraform state cũ được lưu riêng trong [legacy/cloudrescue](legacy/cloudrescue/).

## Mã hiện có

- `terraform/`: mạng hai AZ, S3 riêng tư, control table DynamoDB, ECR, permissions boundary, worker Lambda, Standard Step Functions và đường xử lý execution lỗi.
- `src/cloudhub/catalog.py`: schema của 10 mã mẫu; chặn input ngoài phạm vi và chỉ bật mẫu đã có minh chứng AWS.
- `src/cloudhub/templates/`: T01 Linux, T03 web/RDS, T04 ALB/ASG/RDS, T05 Nginx, T06 ECS Fargate.
- `src/cloudhub/worker.py`: change set, khóa/quota transaction, polling, health, rollback và inventory. Restore PostgreSQL chạy DB trước, bật managed credentials rồi mới triển khai app.
- `apps/`: CRUD, nội dung website và source image Docker mẫu.

Các template đã có mã và kiểm tra cục bộ; **chưa có môi trường CloudHub mới được tạo trên AWS**. `verified_templates` mặc định rỗng. T02/T07/T08/T09/T10 chờ phần triển khai của các thành viên phụ trách. F01/F03/F05 và F06/F08 cần TV2/TV4 tích hợp theo hợp đồng.

## Bắt đầu

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e . -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
```

Hướng dẫn tiếp theo:

- [Tiến độ và các phần còn chờ](docs/tv3-progress.md)
- [Triển khai nền tảng/worker](docs/tv3-deployment.md)
- [Hợp đồng tích hợp TV2/TV4](docs/tv3-contracts.md)
- [Bàn giao và nghiệm thu TV3](docs/tv3-handoff.md)

GitHub Actions chạy kiểm thử, cfn-lint, CloudFormation Guard (kèm trường hợp âm), shell syntax và Terraform validate. Kiểm chứng AWS hiện mới gồm STS/quota, phiên bản RDS và API validate định nghĩa; không đồng nghĩa đã chạy thành công vòng đời môi trường.

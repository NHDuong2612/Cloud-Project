# CloudHub — hạ tầng dùng chung

Terraform ở đây chỉ dành cho hạ tầng chung của CloudHub. Khi khởi tạo, nó sẽ dùng state riêng, tách khỏi `legacy/cloudrescue/terraform/`.

## Thành phần hiện có

| Module | Công dụng | Trạng thái mặc định |
| --- | --- | --- |
| `network` | VPC, hai public subnet ở hai AZ, hai private DB subnet và routing | Tắt |
| `storage` | Bucket S3 riêng tư, mã hóa, versioning để giữ hiện vật phục hồi của CloudHub | Tắt |

Hai module này được điều chỉnh từ phần có thể dùng lại của CloudRescue. Bucket không thay thế snapshot EBS/RDS hay cơ chế AWS Backup của từng mẫu. Hạ tầng chung chưa có API, Cognito, DynamoDB, Step Functions, EventBridge Scheduler hay CloudFormation template cho T01–T10.

## Chuẩn bị

1. Sao chép `terraform.tfvars.example` thành `terraform.tfvars` và điền region, owner, CIDR.
2. Dùng AWS profile của nhóm qua `AWS_PROFILE`; không ghi access key trong mã.
3. Chạy `terraform init`, `terraform validate`, rồi xem `terraform plan` trước khi bật từng module.

Mặc định `enable_network = false` và `enable_storage = false`, nên cấu hình mẫu không tạo tài nguyên. Dùng tên, tag và Terraform state riêng cho CloudHub. Nếu định dùng lại VPC cũ, cần quyết định quyền sở hữu và nhập nó vào state CloudHub có kiểm soát; không trỏ hai state vào cùng tài nguyên.

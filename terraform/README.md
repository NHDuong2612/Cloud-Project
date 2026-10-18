# CloudHub — hạ tầng dùng chung của TV3

Nền tảng network/storage/platform đã triển khai ngày 19/10/2026; [minh chứng và outputs](../docs/evidence/foundation-applied.md). Bản checkout đang có state và cloudhub.auto.tfvars.json cục bộ bị Git ignore; giữ/sao lưu chúng khi vận hành. Các cờ mặc định trong mã dành cho checkout mới, không thay thế cấu hình đang chạy. Orchestrator vẫn tắt.

State ở đây tách khỏi `legacy/cloudrescue/terraform/`. Dùng AWS profile admin hoặc SSO của nhóm để triển khai nền tảng; không cần root. Các workload dùng role riêng được giới hạn quyền, không nhận quyền admin của người triển khai.

| Module | Nội dung | Cờ bật |
| --- | --- | --- |
| network | VPC, hai public subnet và hai private DB subnet trong hai AZ | enable_network |
| storage | Bucket phục hồi riêng tư, mã hóa, versioning, TLS-only | enable_storage |
| platform | DynamoDB control/stream/PITR, bucket deployment, ECR và IAM boundary/deployer | enable_platform |
| orchestrator | Lambda, Step Functions Standard, log, alarm, reconciler và DLQ | enable_orchestrator |

Các cờ mặc định tắt. Điền account ID để provider chặn nhầm tài khoản. Bảng control được bảo vệ bằng prevent_destroy; S3/ECR không force-delete dữ liệu. Bucket recovery không thay thế EBS/RDS snapshot hoặc AWS Backup.

1. Sao chép `terraform.tfvars.example`, điền region/account/owner/CIDR.
2. Chạy preflight, `terraform init`, `terraform validate` và xem plan trước khi triển khai từng module.
3. Sau khi có deployment bucket, build/upload worker bằng key hash, điền worker_s3_key rồi mới bật orchestrator.
4. Giữ verified_templates rỗng cho đến khi có bằng chứng vòng đời AWS với TV2/TV4.

Tài nguyên từng phiên thuộc stack `cloudhub-env-<id>` do F04 quản lý, không nhập vào Terraform state dùng chung. Nếu dùng lại tài nguyên cũ, cần chuyển quyền quản lý state riêng có kiểm soát. Tham khảo [hướng dẫn triển khai](../docs/tv3-deployment.md) và [hợp đồng dữ liệu](../docs/tv3-contracts.md).

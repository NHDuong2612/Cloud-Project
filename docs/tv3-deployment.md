# Triển khai phần TV3

## A03 — nền tảng

Terraform tạo VPC hai AZ, bucket phục hồi riêng tư và (khi bật `enable_platform`) bảng control DynamoDB, bucket mã triển khai riêng và IAM role cho CloudFormation. Bucket mã nguồn tách khỏi bucket dữ liệu người dùng. Các bucket chặn public, mã hóa, versioning và từ chối HTTP. Bảng control bật PITR; Terraform chặn xóa bảng ngoài ý muốn.

Mỗi môi trường có role riêng dưới `/cloudhub/workloads/`, với inline policy chỉ đến secret hoặc prefix của môi trường đó. Permissions boundary giới hạn trần quyền SSM, tải mã ứng dụng, đọc secret RDS và ghi log. Role CloudFormation không được gắn policy quản trị hoặc bỏ boundary. Các API provision EC2/RDS/ALB/ECS cần quyền tạo và describe trong region; chỉ worker nội bộ được phép truyền role này. Đây là quyền điều khiển hạ tầng, không cấp cho người dùng cuối.

1. Cài công cụ dự án: `python -m venv .venv`, sau đó `.venv/Scripts/python -m pip install -e . -r requirements-dev.txt`.
2. Sao chép `terraform/terraform.tfvars.example`; điền đúng account, region, owner và CIDR. Các cờ vẫn tắt theo mặc định.
3. Chạy `python -m cloudhub.preflight --region ap-southeast-1 --expected-account <account> --profile <profile>`; sau khi có VPC, thêm `--vpc-id`. Preflight chỉ đọc STS, Service Quotas và subnet; quota trả về là giới hạn, chưa trừ mức dùng hiện tại.
4. Trong `terraform/`, chạy `terraform init`, `terraform validate`, xem `terraform plan` rồi triển khai những module đã duyệt. Không dùng state ở `legacy/`.
5. Ghi lại outputs platform, VPC và subnet làm cấu hình cho worker F04. Không đưa state, tfvars, secret hoặc credentials lên GitHub.

Auth/Cognito/API, chính sách quota, dự toán và các job sao lưu do TV2/TV4 tích hợp. A03 ở đây cung cấp hạ tầng dùng chung và quyền cho phần TV3; không đánh dấu các phân hệ đó là hoàn thành.

## A07 — worker và Standard Step Functions

1. Chạy `python scripts/package_worker.py`. File `build/worker.zip` có key nội dung `worker/<sha256>.zip` được in ra. Package chỉ dùng standard library và boto3 có trong Lambda runtime.
2. Tải archive lên bucket deployment từ output A03 với key vừa in. Không dùng lại key cho nội dung mới.
3. Điền `worker_s3_key`, bật `enable_orchestrator=true`, giữ `verified_templates=[]` tới khi có minh chứng AWS cho từng mẫu. Chạy lại plan trước apply.
4. Điền `platform_parameters` phần bổ sung cho từng mẫu. Mạng, bucket mã và permissions boundary tự lấy từ outputs nếu đã bật module tương ứng.
5. TV2 lưu request/quota theo [hợp đồng](tv3-contracts.md), rồi gọi workflow. TV4 tích hợp F06, DynamoDB Stream và F08. Alarm workflow và hàng đợi lỗi được xuất để F07 theo dõi.

Kiểm tra ASL bằng `python scripts/validate_workflow.py --profile <profile> --region <region>`. API này chỉ validate định nghĩa, không tạo state machine hoặc Lambda.

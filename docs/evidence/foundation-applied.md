# Nền tảng CloudHub đã triển khai — 19/10/2026

Người dùng đã cho phép tạo nền tảng theo plan 33 thành phần. Đã áp dụng đúng saved plan bằng IAM user **cloudrescue-admin** (profile cục bộ cloudrescue-dev), region **ap-southeast-1**, account **800591602832**.

Kết quả Terraform: **33 added, 0 changed, 0 destroyed**. Sau apply, chạy plan có refresh bằng cấu hình đang dùng: **No changes. Your infrastructure matches the configuration**, exit code 0.

## Tài nguyên bàn giao

- VPC: `vpc-0db3163b28f840a4d`, CIDR `10.30.0.0/16`; DNS support/hostnames bật.
- Public subnet: `subnet-03a545bfb028de840` (ap-southeast-1a, 10.30.1.0/24) và `subnet-0430bafa1dc3a9458` (ap-southeast-1b, 10.30.2.0/24).
- Private DB subnet: `subnet-0931063b300b5d98e` (ap-southeast-1a, 10.30.11.0/24) và `subnet-09deb307146d0ef9e` (ap-southeast-1b, 10.30.12.0/24).
- Internet Gateway: `igw-0d782327f598fdb0a`; public route table: `rtb-00067791bbbeb964f`.
- Deployment bucket: `cloudhub-dev-deployment-800591602832`.
- Recovery bucket: `cloudhub-dev-recovery-800591602832`.
- DynamoDB control table: `cloudhub-dev-control`.
- ECR repository: `800591602832.dkr.ecr.ap-southeast-1.amazonaws.com/cloudhub-dev-approved-apps`.
- CloudFormation deployer: `arn:aws:iam::800591602832:role/cloudhub-dev-environment-deployer`.
- Workload boundary: `arn:aws:iam::800591602832:policy/cloudhub-dev-workload-boundary`.

## Đối chiếu AWS sau khi tạo

- Bốn subnet thuộc hai AZ, không tự gán public IP. Chỉ public route table có default route qua IGW; hai private DB route table chỉ có route local. Không có NAT Gateway trong VPC mới.
- Hai bucket: cả bốn cờ Block Public Access=true; versioning Enabled; SSE AES256; BucketOwnerEnforced; policy Deny khi aws:SecureTransport=false.
- DynamoDB: ACTIVE, PAY_PER_REQUEST, khóa pk/sk, SSE ENABLED, PITR ENABLED, Stream NEW_AND_OLD_IMAGES, TTL ENABLED trên thuộc tính ttl.
- ECR: IMMUTABLE, scanOnPush=true, AES256.
- IAM: trust principal cloudformation.amazonaws.com; quyền StopInstances/StartInstances bị giới hạn theo tag Project=CloudHub; PassRole chỉ tới đường dẫn /cloudhub/workloads/cloudhub-env-* và service EC2/ECS task.
- STS trước/sau triển khai xác nhận cùng IAM user cloudrescue-admin. Không sử dụng root hoặc in credentials.

## Vận hành tiếp theo

State thực nằm tại terraform/terraform.tfstate; cấu hình đang chạy nằm tại terraform/cloudhub.auto.tfvars.json. Cả hai đã kiểm tra bị Git ignore. File cấu hình cục bộ giữ enable_network/storage/platform=true và enable_orchestrator=false để plan tiếp theo phản ánh đúng nền tảng đã duyệt. Sao lưu các file này khi chuyển máy; không khởi tạo state mới cho cùng tài nguyên hoặc dùng state legacy.

Đây là nền tảng dùng chung. Chưa tạo Lambda/Step Functions, EC2/RDS/ALB/Fargate workload và chưa upload artifacts hoặc build/push image. verified_templates vẫn rỗng. Quyền provision workload và toàn bộ vòng đời dữ liệu chưa được chứng minh bởi việc tạo nền tảng thành công. Bước A07 cần plan riêng sau khi chuẩn bị artifacts; các mẫu T04/T06 còn chờ domain/ACM/zone/image và TV2/TV4 tiếp tục tích hợp.

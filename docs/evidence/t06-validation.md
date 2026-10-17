# T06 — kiểm tra ngày 17/10/2026

- cfn-lint và CloudFormation Guard: đạt cho ECS task/service, HTTPS ALB, role riêng và readonly root.
- 15 kiểm thử template/settings/container sample đạt: prefix scope, S3 stream closure, initialize không ghi đè dữ liệu, lỗi storage làm health fail, image digest và CPU/RAM.
- Terraform validate cho ECR repository: đạt.
- Máy chưa có Docker CLI; chưa build/push image. Nhóm chưa có domain/ACM/zone hoặc image ECR được duyệt. Chưa chạy task Fargate thật, chưa backup/restore S3 thật.

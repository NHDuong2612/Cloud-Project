# TV3 — kiểm tra tích hợp ngày 17/10/2026

## Kết quả

- Toàn bộ Python: **57 passed**. Máy Windows có một cảnh báo quyền tạo cache pytest; các kiểm thử hoàn tất thành công.
- `terraform fmt -check -recursive` và `terraform validate`: đạt.
- cfn-lint: đạt cho năm template T01/T03/T04/T05/T06. Kiểm thử Python cũng lint hai template DB-only được sinh khi restore T03/T04.
- CloudFormation Guard: năm template đạt; bảy trường hợp âm đều bị từ chối (EBS không mã hóa, role thiếu boundary, CIDR toàn Internet, CIDR Ref chưa duyệt, DB public, listener HTTP và container root ghi được).
- API AWS `ValidateStateMachineDefinition`: OK, không có diagnostics.
- API AWS `ValidateTemplate`: OK cho năm template và hai biến thể DB-only restore. Các lệnh này chỉ kiểm tra định nghĩa, không tạo stack.
- Worker đã đóng gói cục bộ; key nội dung: `worker/9e67e4c1a88ea886de2e841c14a226777ca804d5da2261f50ac272cbcc35b752.zip`. Chưa upload artifact lên AWS.

## Các thay đổi tích hợp

- PostgreSQL restore tạo DB từ snapshot trước, bật quản lý mật khẩu RDS rồi mới thêm ứng dụng. Worker không đọc giá trị secret.
- Inventory ghi thêm EC2/volume/ENI thuộc ASG, task/ENI thuộc ECS và ENI của EFS mount target để F08 có dữ liệu đối chiếu.
- Xóa theo backup yêu cầu khóa và write-fence của chính operation hiện tại; TV4 phải thực sự ngăn ghi vào workload trước khi sao lưu.
- Có kiểm thử hợp đồng boto3/botocore, gửi operation lặp, restore và inventory phân trang; GitHub Actions chạy lại trên Linux sau mỗi push.

## Chưa được chứng minh

Chưa apply Terraform hoặc tạo môi trường CloudHub thật. Validation không chứng minh đủ quyền IAM, bootstrap, HTTPS, scaling, backup/restore hoặc thu hồi thực tế. Nhóm chưa có domain/Route53/ACM và image ECR được duyệt; máy chưa có Docker CLI. F01/F03/F05 và F06/F08 cần TV2/TV4 tích hợp. Giữ `verified_templates=[]` đến khi có minh chứng vòng đời đầy đủ theo từng phiên bản.

Tài khoản IAM/SSO quản trị có thể dùng triển khai nền tảng; không cần đăng nhập root để thực hiện các hạng mục TV3 này.

# T01 — kiểm tra ngày 17/10/2026

- Template dưới giới hạn inline CloudFormation 51.200 byte, được tạo từ builder có phiên bản.
- cfn-lint ap-southeast-1: đạt.
- Kiểm tra template: IMDSv2, EBS mã hóa, không inbound, permissions boundary và metadata: đạt.
- Bộ quy tắc CloudFormation Guard của dự án kiểm tra cấu hình bảo mật; chạy lại trong CI.
- Chưa chạy EC2 thật hoặc thử snapshot/restore với F06. Mẫu chưa nằm trong verified_templates.

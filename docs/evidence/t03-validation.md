# T03 — kiểm tra ngày 17/10/2026

- AWS DescribeDBEngineVersions xác nhận PostgreSQL 16.15 available trong ap-southeast-1; không tạo database.
- cfn-lint và CloudFormation Guard cho template: đạt.
- 23 kiểm thử liên quan app/template/worker đạt. HTTP CRUD được thử bằng DB giả lập; SQL parameter binding, lỗi 503 đã lọc và TLS verify-full được kiểm tra. Đây chưa phải kiểm tra truy vấn RDS thực tế.
- App bundle được đóng gói theo hash nội dung. Chưa triển khai EC2/RDS mới, chưa có bằng chứng snapshot/restore dữ liệu thật.

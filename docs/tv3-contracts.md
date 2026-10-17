# Hợp đồng tích hợp F02 / F04

## Danh mục mẫu F02

TV2 có thể dùng `cloudhub.catalog.TEMPLATES` để lấy danh sách. `template.public(verified)` trả schema đầu vào cho TV1. Gửi cả mã mẫu và phiên bản cố định, không dùng `latest`.

Có đủ mười mã T01–T10; mẫu chưa có template chỉ là kế hoạch. Mẫu có mã IaC vẫn chưa được bật cho người dùng cho tới khi quản trị thêm `Txx@1.0.0` vào cấu hình `VERIFIED_TEMPLATES` sau kiểm chứng tạo, sử dụng, sao lưu, khôi phục và thu hồi trên AWS. Kiểm thử cục bộ chưa đủ để bật cờ này.

`validate_config(id, version, config)` trả cấu hình chuẩn hóa có giá trị mặc định. Từ chối trường không khai báo, bool thay integer, kích thước vượt giới hạn, CIDR rộng, cặp CPU/RAM Fargate sai và min/desired/max ASG sai. VPC, subnet, role, bucket, chứng chỉ và template URL được lấy từ cấu hình máy chủ; trình duyệt không được tự truyền các giá trị này.

T06 nhận alias image được duyệt; worker ánh xạ alias sang ECR digest cố định. Không nhận Dockerfile, lệnh shell, user data, role ARN hoặc URI image tùy ý.

`backup_scope` mô tả phạm vi dữ liệu cho TV4. Nó chưa tuyên bố có bộ xử lý backup/restore hoạt động. TV4 hoàn thành bộ xử lý và kiểm chứng dữ liệu trước khi mẫu được bật.

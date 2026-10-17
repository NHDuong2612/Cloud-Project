# CloudHub

CloudHub tạo môi trường AWS theo phiên: người dùng chọn mẫu, xem dự toán, xác nhận, sử dụng, sao lưu hoặc khôi phục và kết thúc phiên theo chính sách dữ liệu.

## Phần việc TV3

Theo báo cáo tiến độ, TV3 phụ trách IaC và triển khai: danh mục mẫu F02, điều phối tạo và thu hồi F04, nền tảng AWS và các mẫu EC2, web với RDS, ALB/Auto Scaling, Docker trên ECS Fargate.

Thư mục [`terraform/`](terraform/) là nền hạ tầng dùng chung mới của CloudHub. Hiện nó chỉ chứa mạng hai AZ và bucket S3 riêng tư để lưu hiện vật phục hồi. Mặc định mọi cờ tạo tài nguyên đều tắt. Các phần còn lại của CloudHub sẽ được triển khai tiếp theo kế hoạch nhóm.

Các môi trường T01–T10 sẽ được tạo theo phiên bởi bộ xử lý mẫu và CloudFormation, như kiến trúc trong báo cáo. Mỗi phiên cần ID, tag, danh sách tài nguyên, thời hạn và quy trình thu hồi riêng. Không thêm tài nguyên của phiên vào Terraform state hạ tầng dùng chung.

## Tài nguyên của đề tài cũ

Mã và tài liệu CloudRescue nằm ở [`legacy/cloudrescue/`](legacy/cloudrescue/). Thư mục này giữ cả Terraform state cục bộ của tài nguyên đã từng triển khai; dùng nó để kiểm kê hoặc thu hồi CloudRescue khi nhóm quyết định. Không chạy Terraform CloudHub với state đó.

Chưa có lệnh nào trong lần chuyển đổi này tạo, sửa hoặc xóa tài nguyên AWS.

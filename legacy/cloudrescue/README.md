# CloudRescue — lưu trữ đề tài cũ

Đây là bản lưu cấu hình, tài liệu kiểm kê và Terraform state cục bộ của đề tài CloudRescue (OpenStack → S3 → AWS recovery). Nó không thuộc ứng dụng CloudHub.

Các tài nguyên AWS cũ có thể vẫn tồn tại và tính phí. Trước khi dọn chúng, dùng cấu hình và state trong `terraform/` của thư mục này để kiểm tra trạng thái thực tế và lập kế hoạch thu hồi riêng. Không xóa state hoặc chạy `terraform apply` khi chưa xem plan.

Cấu hình CloudHub đang hoạt động ở `../../terraform/` và dùng state riêng.

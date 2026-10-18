# Tiến độ TV3 — CloudHub

## Bổ sung sau audit ngày 19/10/2026

Kiểm tra cuối: **114 kiểm thử đạt**. Xem [kết quả và giới hạn kiểm chứng](evidence/post-audit-validation.md). Có thêm bản sửa khởi tạo S3 T06 không cần ListBucket (`6a5a825`).

- `4c57dba`: quyền EC2 update giới hạn instance có tag CloudHub.
- `af969f1`: worker nhận renew, reservation ràng buộc hạn mới, transaction kiểm tra expiry/version/lock; TV2/TV4 cần tích hợp API/F03/scheduler theo hợp đồng.
- `3bc0707`: F04 nhận kết quả copy/verify prefix S3 T06 từ F06; TV4 vẫn triển khai và chứng minh copy thật.
- `6305498`: AllocatedStorage theo config cả sau restore, kiểm tra dung lượng snapshot và mức tăng tối thiểu.
- `12ce4e1`: bộ chạy ASL cục bộ, response loss/retry/deadline/interrupt; giữ khóa khi NEEDS_ATTENTION.
- Có công cụ workload_probe và [kịch bản nghiệm thu A22/A24](tv3-acceptance.md), chưa thay thế bài chạy AWS thật.
- Người dùng đã duyệt và đã apply nền tảng: 33 thêm, 0 sửa, 0 xóa; plan sau apply không có thay đổi. Xem [minh chứng AWS thật](evidence/foundation-applied.md).

Mỗi hạng mục có một commit riêng, được đẩy lên GitHub trước khi bắt đầu hạng mục tiếp theo. "Kiểm tra cục bộ" không đồng nghĩa "đã triển khai và nghiệm thu trên AWS".

| Thứ tự | Hạng mục | Phạm vi | Trạng thái |
| --- | --- | --- | --- |
| 0 | Chuyển đề tài | Tách state CloudRescue; giữ lại mạng và S3 dùng được | Đã dọn mã |
| 1 | A03 | IaC nền tảng TV3, cấu hình triển khai và kiểm tra quyền/quota | Đã apply 33 thành phần nền tảng; đã đối chiếu AWS và plan sau apply No changes |
| 2 | F02 | Danh mục phiên bản mẫu, schema đầu vào, hợp đồng với TV2/TV4 | Đã viết catalog/schema và kiểm thử; mẫu chỉ bật sau kiểm chứng AWS |
| 3 | A07 / F04 | Step Functions, worker CloudFormation, khóa tác vụ, health check, rollback, inventory | Đã viết worker/workflow và IaC; kiểm thử cục bộ và ASL AWS đạt; chưa chạy vòng đời AWS |
| 4 | A10 / T01 | Linux EC2/EBS qua SSM | Đã có template và kiểm thử; chờ kiểm chứng vòng đời với TV4 trên AWS |
| 5 | A12 / T03 | Web CRUD và RDS riêng tư | Đã có template, demo CRUD và kiểm thử; chờ kiểm chứng RDS/restore thật |
| 6 | A13 / T04 | HTTPS ALB, ASG có giới hạn, RDS | Đã có template và kiểm thử; chờ domain/ACM/Route53 và kiểm chứng AWS |
| 7 | A14 / T05 | Web server EC2, phối hợp TV1 | Đã có mẫu Nginx và bundle mẫu; chờ TV1 duyệt nội dung, TV4 kiểm chứng restore |
| 8 | A16 / T06 | ECS Fargate với image được duyệt | Đã có template, image source và kiểm thử; chờ domain/ACM/image được duyệt |
| 9 | Bàn giao TV3 | Kiểm tra tích hợp, hướng dẫn TV2/TV4, các phần TV3 hỗ trợ | Đã bổ sung staged RDS restore, inventory động, SDK contract tests và hướng dẫn bàn giao; chờ nghiệm thu AWS/liên thành viên |

TV4 phụ trách sao lưu/khôi phục (F06), scheduler cuối phiên và xác minh sau thu hồi (F08). TV2 phụ trách auth, API, quota và dự toán (F01/F03/F05). TV3 cung cấp giao diện tích hợp; trạng thái cuối phiên chỉ được xác nhận sau kết quả F08.

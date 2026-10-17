# Tiến độ TV3 — CloudHub

Mỗi hạng mục có một commit riêng, được đẩy lên GitHub trước khi bắt đầu hạng mục tiếp theo. "Kiểm tra cục bộ" không đồng nghĩa "đã triển khai và nghiệm thu trên AWS".

| Thứ tự | Hạng mục | Phạm vi | Trạng thái |
| --- | --- | --- | --- |
| 0 | Chuyển đề tài | Tách state CloudRescue; giữ lại mạng và S3 dùng được | Đã dọn mã |
| 1 | A03 | IaC nền tảng TV3, cấu hình triển khai và kiểm tra quyền/quota | Terraform validate đạt, 3 kiểm thử đạt, preflight AWS chỉ đọc đạt; chưa apply |
| 2 | F02 | Danh mục phiên bản mẫu, schema đầu vào, hợp đồng với TV2/TV4 | Đã viết catalog/schema và kiểm thử; mẫu chỉ bật sau kiểm chứng AWS |
| 3 | A07 / F04 | Step Functions, worker CloudFormation, khóa tác vụ, health check, rollback, inventory | Đã viết worker/workflow và IaC; kiểm thử cục bộ và ASL AWS đạt; chưa chạy vòng đời AWS |
| 4 | A10 / T01 | Linux EC2/EBS qua SSM | Đã có template và kiểm thử; chờ kiểm chứng vòng đời với TV4 trên AWS |
| 5 | A12 / T03 | Web CRUD và RDS riêng tư | Chưa triển khai |
| 6 | A13 / T04 | HTTPS ALB, ASG có giới hạn, RDS | Chưa triển khai |
| 7 | A14 / T05 | Web server EC2, phối hợp TV1 | Chưa triển khai |
| 8 | A16 / T06 | ECS Fargate với image được duyệt | Chưa triển khai |
| 9 | Bàn giao TV3 | Kiểm tra tích hợp, hướng dẫn TV2/TV4, các phần TV3 hỗ trợ | Chưa triển khai |

TV4 phụ trách sao lưu/khôi phục (F06), scheduler cuối phiên và xác minh sau thu hồi (F08). TV2 phụ trách auth, API, quota và dự toán (F01/F03/F05). TV3 cung cấp giao diện tích hợp; trạng thái cuối phiên chỉ được xác nhận sau kết quả F08.

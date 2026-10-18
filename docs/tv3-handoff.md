# Bàn giao TV3

Đọc bổ sung [kết quả sau audit 19/10](evidence/post-audit-validation.md), [kịch bản A22/A24](tv3-acceptance.md), [restore T06](t06-restore-contract.md), [RDS storage](rds-storage-contract.md) và [phục hồi workflow](workflow-recovery.md). Mã đã có gia hạn; API/quota/scheduler vẫn cần phối hợp theo hợp đồng. Bản evidence mới phân biệt kiểm thử cục bộ với các bước AWS còn chờ.

## Các hạng mục đã có mã

| Hạng mục | Đầu ra |
| --- | --- |
| A03 | Terraform nền tảng, boundary và role, preflight account/quota |
| F02 | Danh mục 10 mã, schema, phiên bản và cơ chế bật sau kiểm chứng |
| A07/F04 | Standard workflow, change set/preview/confirmation, khóa/quota transaction, health, rollback, inventory và execution reconciliation |
| A10/T01 | Linux/SSM/EBS, đầu vào restore snapshot đã duyệt |
| A12/T03 | CRUD với private PostgreSQL/TLS/managed secret, staged restore adapter |
| A13/T04 | HTTPS ALB/ASG/CPU target tracking, signal-gated rolling update |
| A14/T05 (hỗ trợ) | Nginx và bundle website, giữ nội dung sau restore |
| A16/T06 | ECS Fargate, ECR digest allowlist, role dữ liệu S3 riêng, source image mẫu |
| A21 (hỗ trợ) | Inventory ASG/ECS/EFS child IDs và giữ chốt xác minh cho F08 |

Các commit từng phần đã được đẩy lần lượt lên main. Danh sách thay đổi xem Git log; tài liệu và kết quả kiểm tra trong docs/evidence. Không có thao tác tạo/sửa/xóa tài nguyên AWS thật trong quá trình viết mã; các API đã gọi chỉ đọc/validate.

## Tích hợp với thành viên khác

- TV1: dùng schema catalog, hiển thị dự toán/tiến trình từ API, duyệt nội dung T05 và image T06. Các trang trong apps là demo workload, không phải frontend quản trị CloudHub.
- TV2: xác thực owner, ghi META/OP/quota bằng transaction, gọi F04, lọc kết quả theo quyền sở hữu. Kiểm tra API không cho user sửa owner, role, subnet, image URI hoặc operation đang chạy. Quyền admin dùng để dựng platform, không cấp xuống user hoặc workload.
- TV4: F06 kiểm tra và sao lưu dữ liệu, F08 xác minh/hoàn quota, scheduler đọc lại expiry/version. Giữ write fence thực tế: T03 có thể dừng app trước snapshot; T04 cần ngừng traffic và các tiến trình ASG có thể thay máy rồi dừng ghi; T06 cần ngừng traffic/drain và dừng task trước sao lưu prefix. Chỉ đổi flag trong DynamoDB không ngăn ứng dụng ghi dữ liệu.
- A17/T09: TV2 cung cấp template, schema API/backup và readiness adapter; TV3 hỗ trợ đăng ký phiên bản/role/workflow. Chưa có Lambda/API/DynamoDB workload T09 trong repo này.
- A18/T08: TV4 cung cấp EFS/two-client template và backup/restore. TV3 đã có mở rộng inventory mount-target ENI; F08 gỡ phụ thuộc mount target/SG trước khi xác nhận thu hồi. Chưa có template EFS T08 trong repo này.

## Trước khi bật mẫu

1. Tích hợp F01/F03/F05 và F06/F08; chạy kiểm thử quyền chéo, tranh quota, gửi lặp, khởi động lại và tác vụ bị dừng.
2. Deploy nền tảng với admin/SSO sau khi xem plan. Build/upload worker và app artifacts đúng key hash.
3. T01/T03/T05: thử truy cập, ghi dữ liệu, quiesce, backup, restore sang ID mới, đối chiếu dữ liệu và thu hồi; lưu kết quả F08.
4. T04: bổ sung domain/zone/ACM, thử HTTPS, tải, scaling trong giới hạn, rolling failure và phục hồi dữ liệu RDS. Hiện nhóm chưa có các cấu hình này.
5. T06: có Docker/build runner, build Linux amd64, push ECR, duyệt digest; thử write S3, thay task, backup/restore prefix, thu hồi và kiểm kê log/data giữ lại. Hiện chưa có Docker CLI/image được duyệt/domain.
6. Ghi nguồn/thời điểm chi phí bằng F03/F07; không dùng quota limit hoặc kiểm thử giả lập làm bằng chứng chi phí/hiệu năng thực tế. Bật verified_templates theo đúng version sau nghiệm thu.

Backup restore và xác minh thu hồi toàn hệ thống chưa hoàn tất khi các thành viên chưa tích hợp. Bộ kiểm thử cục bộ chứng minh logic và hợp đồng SDK; nó không chứng minh IAM đầy đủ hoặc dịch vụ AWS đã provision thành công.

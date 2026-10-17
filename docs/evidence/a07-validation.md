# A07 — kiểm tra ngày 17/10/2026

- 12 kiểm thử worker đạt: tranh khóa, owner/version, điều kiện backup, bước chờ F08, thời điểm bắt đầu phiên, giữ expiry khi update, giữ nguồn khi update lỗi, phân biệt lỗi quyền với tài nguyên mất, inventory nhiều trang, chặn replacement, transaction quota/khóa và lọc lỗi nhạy cảm.
- AWS ValidateStateMachineDefinition cho Standard workflow: OK, không có diagnostic; không tạo state machine.
- Terraform validate cho module orchestrator: đạt.
- Chưa chạy integration với F01/F03/F05 của TV2 hoặc F06/F08 của TV4. Đây là hợp đồng tích hợp, chưa chứng minh backup/restore/thu hồi toàn hệ thống.

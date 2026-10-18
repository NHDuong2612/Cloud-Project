# Kết quả sau audit — 19/10/2026

Cập nhật sau báo cáo này: người dùng đã duyệt và nền tảng đã triển khai; xem [foundation-applied.md](foundation-applied.md). Phần còn chờ dưới đây ghi nhận thời điểm trước khi nhận được sự đồng ý.

## Mã đã hoàn thành và đẩy từng phần

- 4c57dba: bổ sung quyền EC2 update theo phạm vi instance/tag.
- af969f1: renew với version, expiry, khóa và reservation ràng buộc thời lượng.
- 3bc0707: nhận kết quả restore/copy S3 T06 đã kiểm chứng từ F06.
- 6305498: truyền dung lượng RDS trong restore/update, kiểm tra source snapshot size và mức tăng tối thiểu.
- 12ce4e1: workflow offline từ ASL thật, worker restart, response loss, retry, deadline, interruption; giữ khóa NEEDS_ATTENTION.
- 1380e53: công cụ đối chiếu marker/digest và kịch bản A22/A24; plan nền tảng.
- 6a5a825: sửa khởi tạo note T06 với role không có ListBucket; conditional write và retry 409 có giới hạn.

## Kiểm tra

- Toàn bộ Python hiện tại: **114 passed**, không dùng AWS thật cho các kiểm thử.
- Terraform fmt/validate và plan nền tảng: đạt; plan có **33 add, 0 change, 0 destroy**.
- cfn-lint và Guard cho năm template: đạt; bảy cấu hình không an toàn đều bị Guard từ chối.
- AWS ValidateTemplate: bảy kết quả OK (năm template và hai DB-only restore stage).
- AWS ValidateStateMachineDefinition sau thêm nhánh renew: OK, diagnostics rỗng.
- Worker ZIP mới: `worker/f65f91ae3f510b7fce9a8f3483e32fb300180cd839b101ae32ce7233d6ecd5dd.zip`.
- CRUD ZIP: `apps/crud/2864fe6c116c36326fc806dbb3a8709a7f2740525ad724eade77b975d5a6078c.zip`.
- Website ZIP: `apps/website/2a6ae9d89ef623ec6e6f30b462a8bb53d47f0e1315c9bb989f9663c96f4fd2ce.zip`.

Các ZIP/plan ở build, không commit hoặc upload lên AWS. GitHub Actions chạy Python 3.12, template lint/Guard/shell syntax và Terraform sau mỗi push; xem trạng thái từng commit trên GitHub.

## Còn chờ

Chưa apply plan hoặc tạo workload CloudHub. Yêu cầu nhóm đồng ý tạo nền tảng đã được gửi cùng phạm vi plan; chưa có phản hồi tại thời điểm ghi kết quả. Không suy ra đồng ý từ việc chờ. Không có thay đổi tài nguyên AWS trong đợt viết mã/plan này.

Domain/zone/ACM, Docker build runner và image ECR được duyệt vẫn chưa có. API auth/F03/F05, scheduler, F06 copy/snapshot thực và F08 cần TV2/TV4 tích hợp. Bộ chạy ASL và SDK Stubber chưa chứng minh IAM, transaction contention hoặc restore dữ liệu trên dịch vụ AWS. Giữ mẫu chưa bật cho user đến khi có minh chứng vòng đời đầy đủ.

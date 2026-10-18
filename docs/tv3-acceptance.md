# A22/A24 — kịch bản nghiệm thu phần TV3

## Chuẩn bị chung

- Dùng tài khoản/region đã kiểm tra bằng preflight, môi trường lab riêng, owner và ID môi trường mới. Không dùng state legacy. Xem plan và chi phí trước khi apply; plan nền tảng hiện có 33 thành phần thêm mới, không sửa/xóa, chưa gồm workload.
- Production giữ verified_templates rỗng. Kiểm chứng template trực tiếp bằng change set quản trị, hoặc dùng một worker/workflow lab riêng chỉ admin được gọi với allowlist của đúng mẫu đang thử. Không bật mẫu cho người dùng để thực hiện lần kiểm chứng đầu tiên.
- Chụp thời điểm UTC và version/commit; ghi account/region, environment_id/operation_id, cấu hình, stack ID, AWS IDs, trạng thái từng bước, thời lượng, kết quả probe, recovery point/manifest và inventory F08. Không đưa secret, state, credentials hoặc dữ liệu cá nhân vào minh chứng GitHub.
- Tạo mới, dùng, backup, restore, update, renew, delete và F08 phải được đánh giá riêng. READY hoặc snapshot completed không thay thế kiểm chứng dữ liệu. Phần F01/F03/F05/F06/F08 còn thiếu được ghi rõ, không ghi PASS giả.

## T01 — Linux, không cần domain/image

1. Tạo từ template/change set đã xem; chờ SSM Online. Ghi AMI/root volume và access path.
2. Trong phiên SSM, tạo file marker riêng với chuỗi ngẫu nhiên; đồng bộ dữ liệu. TV4 thực hiện quiesce và snapshot, ghi nguồn/owner/AMI/volume size.
3. Restore sang ID mới qua job được duyệt. Đọc lại marker và checksum qua SSM; so sánh byte, không chỉ sự tồn tại của file.
4. Preview đổi t3.micro sang t3.small; xác nhận tác động khởi động lại. Kiểm tra loại máy thực tế, SSM kết nối lại và marker giữ nguyên. Thử thay đổi yêu cầu replacement: phải từ chối, nguồn còn nguyên.
5. Gia hạn READY trước hết hạn, gửi lại operation và đối chiếu hạn/version chỉ đổi một lần. Cho lịch thu hồi cũ chạy và xác nhận bị từ chối bởi điều kiện expiry/version/lock.
6. Backup rồi thu hồi, đối chiếu instance/volume/ENI và bản sao giữ lại qua F08. Không dùng terraform destroy nền tảng chung để dọn một phiên.

## T03 — CRUD/RDS, không cần domain/image

1. Upload bundle bằng key hash; tạo EC2 và RDS private; truy cập qua CIDR lab hoặc SSM tunnel. Ghi DB size thực tế và managed-secret pointer, không đọc/in giá trị secret để làm minh chứng.
2. Trên workload lab riêng, chạy `python scripts/workload_probe.py --template T03 --url http://localhost:8080 --allow-http --write-marker`. Lưu marker trong JSON đầu ra. Thao tác này ghi một task thử nghiệm.
3. TV4 ngừng ghi rồi tạo snapshot. Ghi source_allocated_storage_gb từ metadata snapshot. Restore sang ID mới, quan sát DB-only → managed credentials active → application stage.
4. Trên URL/tunnel của bản restore, chạy `python scripts/workload_probe.py --template T03 --url http://localhost:8081 --allow-http --marker <marker_nguon>`. Không dùng write-marker tại bản restore: phải chứng minh dữ liệu nguồn đã có sẵn.
5. Snapshot 40 GiB: thử restore 20/41 GiB bị từ chối; 40/44 GiB hợp lệ. Preview/update bản restore 40 → 44 GiB; đối chiếu AllocatedStorage thực và marker còn nguyên, DB không bị replacement. Tôn trọng cửa sổ storage optimization của RDS trước lần tăng tiếp theo.
6. Thử lỗi bootstrap/health trên lab; kiểm tra rollback mới và không xóa nguồn khi update lỗi. Thu hồi qua F06/F08, báo cáo final snapshot và phí/hạn lưu còn lại.

## T05 — website, không cần domain/image

1. Upload bundle website bằng key hash. Tạo máy, xác nhận /health và website.
2. Chạy `python scripts/workload_probe.py --template T05 --url http://localhost:8080 --allow-http` để lấy SHA256 nội dung index. Thay nội dung thử nghiệm trong lab rồi lấy lại digest trước backup.
3. TV4 snapshot/restore sang ID mới; probe URL bản restore với `--expected-sha256 <digest_nguon>`. Chứng minh bootstrap không seed đè nội dung; đối chiếu thêm các asset/file đã thay trong SSM.
4. Thu hồi và F08 như T01. Probe index không thay thế checksum toàn bộ website.

## T04/T06 — phần chạy thật còn chờ

- T04: domain/zone/ACM đúng account/region, app bundle. Thử HTTPS, health, dữ liệu RDS, rolling update thất bại và tải có giới hạn; đo min/desired/max thực, CPU/time-to-scale và số máy không vượt max. TV1/TV4 chọn bộ tải; dừng tải sau cửa sổ đã ghi và theo dõi hóa đơn. Không lấy số từ mock làm kết quả hiệu năng.
- T06: build Linux amd64, push ECR và duyệt digest; cấu hình HTTPS. Dùng probe T06 write-marker trên một note lab riêng (ghi đè note hiện tại). TV4 copy/verify prefix theo t06-restore-contract; dùng probe read-only với marker nguồn trên service restore. Thay task và đối chiếu S3 vẫn còn dữ liệu; F08 phân loại ENI/task/log/prefix giữ lại.

## Nhánh lỗi và phối hợp

- Sai owner/version/config hash, quota hết hạn, yêu cầu trùng: từ chối trước provision; xác minh cả API TV2 lẫn worker.
- Hai yêu cầu đồng thời: chỉ một transaction lấy khóa. Gia hạn và claim-expiry của TV4 phải dùng cùng điều kiện READY/version/expiry/no-lock, không chỉ so đồng hồ trên client.
- Mất phản hồi ở create/execute hoặc sau commit gia hạn; khởi động lại worker; retry hết giới hạn; dừng execution; hết deadline; lỗi backup và delete: kiểm tra trạng thái bền vững, dữ liệu nguồn và khóa còn giữ. Theo workflow-recovery.md, không force-unlock khi AWS chưa ổn định.
- Chỉ đóng A22/A24 khi có báo cáo PASS/FAIL cho từng bước, sự cố còn lại, chi phí có nguồn/thời điểm, F08 và dữ liệu restore. Công cụ probe và kiểm thử local hiện mới là công cụ chuẩn bị nghiệm thu.

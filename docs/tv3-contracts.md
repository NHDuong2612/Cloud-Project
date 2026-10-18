# Hợp đồng tích hợp F02 / F04

## Danh mục mẫu F02

TV2 có thể dùng `cloudhub.catalog.TEMPLATES` để lấy danh sách. `template.public(verified)` trả schema đầu vào cho TV1. Gửi cả mã mẫu và phiên bản cố định, không dùng `latest`.

Có đủ mười mã T01–T10; mẫu chưa có template chỉ là kế hoạch. Mẫu có mã IaC vẫn chưa được bật cho người dùng cho tới khi quản trị thêm `Txx@1.0.0` vào cấu hình `VERIFIED_TEMPLATES` sau kiểm chứng tạo, sử dụng, sao lưu, khôi phục và thu hồi trên AWS. Kiểm thử cục bộ chưa đủ để bật cờ này.

`validate_config(id, version, config)` trả cấu hình chuẩn hóa có giá trị mặc định. Từ chối trường không khai báo, bool thay integer, kích thước vượt giới hạn, CIDR rộng, cặp CPU/RAM Fargate sai và min/desired/max ASG sai. VPC, subnet, role, bucket, chứng chỉ và template URL được lấy từ cấu hình máy chủ; trình duyệt không được tự truyền các giá trị này.

T06 nhận alias image được duyệt; worker ánh xạ alias sang ECR digest cố định. Không nhận Dockerfile, lệnh shell, user data, role ARN hoặc URI image tùy ý.

`backup_scope` mô tả phạm vi dữ liệu cho TV4. Nó chưa tuyên bố có bộ xử lý backup/restore hoạt động. TV4 hoàn thành bộ xử lý và kiểm chứng dữ liệu trước khi mẫu được bật.

## Dữ liệu F05 và nhận tác vụ F04

Bảng control dùng khóa `pk=ENV#<environment_id>` và `sk`. ID môi trường và tác vụ là `uuid.uuid4().hex` (32 ký tự hex). TV2 xác thực owner từ token; không lấy owner, stack ARN hoặc template URL tùy ý từ trình duyệt. Các record dưới đây được TV2 ghi bằng transaction cùng cập nhật quota phía server trước khi gọi F04.

- `sk=META`: `owner_id`, `version` (integer), `template_id`, `template_version`, `config` đã chuẩn hóa, `duration_minutes` 15–480, `retention_policy` là `backup` hoặc `purge`, `status=REQUESTED` khi tạo. Các lần tiếp theo dùng version hiện tại và trạng thái READY. `lock_owner` do F04 điều khiển.
- `sk=OP#<operation_id>`: `operation_id`, `owner_id`, `action` (`create`, `plan_update`, `update`, `renew`, `delete`), `expected_version`, `status=QUEUED`. Create/update có `quota_reservation_id` và `config_hash` từ `cloudhub.worker.configuration_hash(config)`. Cấu hình update gửi đầy đủ giá trị chuẩn hóa trong `config`.
- `sk=QUOTA#<reservation_id>`: `owner_id`, `operation_id`, `config_hash`, `status=RESERVED`, `valid_until` Unix epoch. F03 cần giữ quota thật bằng cập nhật có điều kiện/transaction; một chuỗi reservation ID tự nó không đủ. F04 kiểm tra record rồi tiêu thụ nó trong cùng transaction lấy khóa. Reservation đã CONSUMED không tự hết hạn; F03/F08 giải phóng sau khi đối chiếu tài nguyên. Không dùng TTL để tự hoàn quota đang sử dụng.

Sau khi lưu, TV2 dùng `cloudhub.operations.start_execution(client, workflow_arn, environment_id, operation_id)` và trả HTTP 202. Tên execution là operation ID để chống gửi lặp. IAM policy gọi workflow nằm ở Terraform output `deployment_workflow.start_execution_policy`. Không cấp quyền StartExecution trực tiếp cho trình duyệt; chỉ backend đã xác thực.

Workflow chỉ lưu ID và kết quả gọn trong execution history. Worker đọc cấu hình từ DynamoDB, tạo change set, chờ AWS bằng Wait state, thử lại lỗi tạm thời và ghi inventory từng resource bằng paginator. Không giữ Lambda chạy chờ RDS. Hạn phiên bắt đầu khi health check đạt; update không tự gia hạn.

## Đổi cấu hình

Danh mục công bố cả `plan_update` và `update`; xác nhận dùng đúng change set đã preview. T06 có hợp đồng restore S3 riêng tại [t06-restore-contract.md](t06-restore-contract.md); không truyền S3 URI hoặc prefix tùy ý vào template.

Gửi `plan_update` với config chuẩn hóa. Kết quả PREVIEWED chứa `change_set_id`, `config`, `expected_version`, `changes` trong operation record. Sau khi người dùng xem dự toán và chấp nhận tác động, TV2 đặt reservation quota mới và gửi operation `update` với `preview_operation_id`, `confirmed_change_set_id`, cùng `config` chính xác của preview. F04 kiểm tra lại owner/version và từ chối change set có replacement. Không hỗ trợ thu nhỏ volume hoặc storage RDS.

## Gia hạn phiên

TV2 tạo operation `renew` sau khi xác thực owner và xác nhận dự toán mới. Gửi `expected_version`, `expected_expires_at_epoch` (hạn hiện tại) và `new_expires_at_epoch` (hạn mới tuyệt đối). Không đổi cấu hình khi gia hạn. F03 giữ phần chi phí/thời gian tăng thêm, không đếm môi trường thành hai suất quota. Hash reservation và operation là `configuration_hash({"config": config_chuan_hoa, "expires_at_epoch": new_expires_at_epoch})` để không dùng lại dự toán cho thời lượng khác.

Chỉ gia hạn phiên READY chưa hết hạn, tổng thời lượng không quá 480 phút kể từ ready_at, theo phút tròn. Transaction lấy khóa kiểm tra owner/version/status/hạn cũ/phiên chưa hết hạn và tiêu thụ reservation. F04 ghi hạn mới, tổng duration_minutes, tăng version và hoàn tất SUCCEEDED trong transaction; gửi lại operation không cộng thêm giờ. Không thay stack AWS.

Scheduler TV4 phải dùng điều kiện owner/version/status READY, không có lock_owner, đúng expires_at_epoch đã đọc và expires_at_epoch <= now khi chuyển FINALIZING. Nếu gia hạn lấy khóa trước, lịch cũ bị từ chối; nếu thu hồi lấy khóa trước, gia hạn bị từ chối. Stream phát record READY mới để cập nhật lịch. Mã scheduler/API/F03 vẫn thuộc TV2/TV4; chưa tuyên bố có endpoint gia hạn hoặc scheduler vận hành.

## Thu hồi và phối hợp TV4

F06 cần hạn chế ghi và ổn định dữ liệu trước khi sao lưu cuối phiên. TV4 giữ `lock_owner=<operation_id>`, `write_fence_operation_id=<operation_id>` và trạng thái FINALIZING trên META, sau đó ghi `sk=BACKUP#<job_id>`: `status=COMPLETED`, `owner_id`, `source_version`, `source_quiesced=true`, `operation_id` và `recovery_point`. Operation delete tham chiếu `backup_job_id`. Cả khóa và write fence phải còn được giữ, không chỉ có bản sao cũ hoàn tất. Sao lưu thất bại hoặc khác version thì F04 không xóa stack. Chính sách purge chỉ được chạy khi META đã ghi `retention_policy=purge` và operation do backend ghi `purge_confirmed=true` sau xác nhận của chủ môi trường.

Sau delete-stack, F04 ghi `AWAITING_VERIFICATION`, operation `WAITING_F08`, giữ khóa và inventory. Đây chưa phải xác nhận sạch tài nguyên. F08 đối chiếu API AWS, snapshot/volume giữ lại, hạn lưu và phí; sau đó mới ghi RELEASED hoặc NEEDS_ATTENTION, tăng version, hoàn quota phù hợp và bỏ khóa bằng transaction có điều kiện. RDS snapshot/EBS được giữ theo template phải xuất hiện trong báo cáo, không được xem như đã xóa hết.

Control table có DynamoDB Stream để TV4 nhận thay đổi READY và `expires_at_epoch`. Scheduler đọc lại expiry/version trước khi khóa; gia hạn hợp lệ phải cập nhật có điều kiện, không thu hồi theo lịch cũ.

Khôi phục tạo environment mới và operation `create`, có `restore_job_id` trên META. F06 ghi `sk=RESTORE#<job_id>` trong partition môi trường mới: `status=APPROVED`, `owner_id`, `operation_id`, `ownership_verified=true`, `template_id`, `template_version`, `parameters`. T01/T05 chỉ nhận cặp RootSnapshotId/SourceAmiId; T03/T04 chỉ nhận DBSnapshotIdentifier. F06 phải kiểm tra snapshot nguồn, owner, account/region, AMI, kích thước volume và phiên bản ứng dụng trước khi duyệt. F04 không nhận các trường restore từ trình duyệt hoặc trong config của người dùng.

Với PostgreSQL, F04 tạo database-only stack từ snapshot với managed-password tắt, gọi ModifyDBInstance để bật managed credentials, chờ DB available/secret active rồi tạo change set cập nhật cùng stack để thêm web tier. Worker chỉ đọc trạng thái/ARN pointer, không đọc giá trị secret. Không chạy trực tiếp full template với snapshot để bỏ qua quy trình này. Cấu hình nguồn được giữ cho những lần update tiếp theo.

Inventory mở rộng CFN resource IDs thành instance/volume/ENI của ASG, task/ENI của ECS và ENI của EFS mount target. Mỗi record có parent ID, loại tài nguyên và thời điểm quan sát. F08 vẫn phải kiểm tra lại trạng thái thực tế và scan tag để tìm snapshot/nguồn giữ lại được tạo sau delete; lỗi AccessDenied không được xem như tài nguyên đã mất.

Execution bị dừng hoặc timeout được EventBridge chuyển sang NEEDS_ATTENTION; worker không tự xóa stack update hoặc mở khóa cho tác vụ mới. Quản trị cần đối chiếu CloudFormation còn đang chạy, inventory và chính sách dữ liệu trước khi phục hồi tác vụ. Không force-unlock khi AWS còn tạo tài nguyên.

# Hợp đồng khôi phục T06 giữa TV3 và TV4

F06 sao chép và kiểm chứng dữ liệu trước khi F04 tạo service. Đích luôn là RecoveryBucketName của platform và `environments/<environment_id_moi>/data/`. Tạo ID môi trường mới; kiểm tra đích chưa được môi trường khác sử dụng. Không cho trình duyệt ghi record RESTORE, metadata kiểm chứng hoặc URI đích.

Trong partition ENV của môi trường mới, TV4 ghi RESTORE với status APPROVED, owner_id, operation_id, ownership_verified=true, template_id=T06, template_version=1.0.0 và parameters là object rỗng. Thêm data_copy:

```json
{
  "status": "VERIFIED",
  "destination_bucket": "<RecoveryBucketName>",
  "destination_prefix": "environments/<environment_id_moi>/data/",
  "container_image": "<ECR URI voi digest dung trong approved_images>",
  "object_count": 1,
  "verified_at_epoch": 1790000000,
  "manifest_sha256": "<64 ky tu hex thuong>",
  "source_backup_id": "backup-1"
}
```

F06 chịu trách nhiệm xác minh owner của bản sao nguồn, version từng object, checksum, schema/image compatibility, số object và nội dung đích; lưu manifest có checksum theo canonical format do F06 quy định. VERIFIED là kết quả nghiệp vụ từ backend tin cậy, không phải cờ do user gửi. Kiểm tra checksum sau copy, hoàn tất mới phê duyệt; không sửa prefix trong lúc F04 triển khai. Empty dataset chỉ hợp lệ nếu manifest xác nhận 0 object và ứng dụng cho phép khởi tạo dữ liệu rỗng.

F04 kiểm tra lại owner/operation/template, bucket/prefix đích, digest image, manifest hash, số object và thời điểm kiểm chứng. Record không khớp hoặc copy còn đang chạy bị từ chối trước khi tạo stack. F04 không tự copy hoặc đọc nội dung S3, nên không mở thêm quyền S3 cho worker. Nó lưu restored_data vào operation trước khi provision để F08 thấy prefix ngay cả khi tạo stack thất bại. Sau READY, descriptor được giữ trên META.

Image mẫu khởi tạo note bằng If-None-Match và giữ nguyên object đã khôi phục. Mỗi image được duyệt phải kiểm chứng hành vi này. Nếu provision thất bại, prefix phục hồi được giữ để TV4/F08 xử lý theo hạn lưu, không tự xóa dữ liệu. Có kiểm thử handshake cục bộ; chưa có job copy/restore S3 thật hoặc service Fargate thật. TV4 vẫn phải triển khai F06 và chứng minh manifest, dữ liệu khôi phục.

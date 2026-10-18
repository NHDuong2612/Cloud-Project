# T06 — khởi tạo prefix S3 rỗng, 19/10/2026

Task role chỉ có GetObject/PutObject trên prefix riêng, không có ListBucket. Theo [GetObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html), khi thiếu ListBucket, object chưa tồn tại có thể trả AccessDenied 403 thay vì NoSuchKey 404. Luồng GET trước PUT cũ vì vậy có thể không khởi tạo được note.

Image source mới khởi tạo bằng PutObject If-None-Match ngay, không cần GET/ListBucket. PreconditionFailed giữ nguyên dữ liệu hiện có/restore. ConditionalRequestConflict thử lại tối đa ba lần theo [PutObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html), không xem 409 là bằng chứng dữ liệu đã tồn tại. Các lỗi quyền/transport được lọc thành STORAGE_UNAVAILABLE, không mở thêm quyền bucket.

Có kiểm thử SDK Stubber cho conditional PutObject và hồi quy empty-prefix/412/409. Chưa build/push image mới hoặc chạy Fargate thật; digest mẫu chỉ được duyệt sau khi build và kiểm chứng.

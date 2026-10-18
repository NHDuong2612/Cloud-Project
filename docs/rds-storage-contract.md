# Dung lượng RDS khi khôi phục và cập nhật

T03/T04 luôn truyền DBStorage xuống AllocatedStorage, kể cả database-only restore stage, application stage và update sau restore. DBSnapshotIdentifier giữ nguyên giá trị nguồn; không đổi snapshot để tăng dung lượng. MasterUsername/DBName/StorageEncrypted vẫn được bỏ khi restore theo ràng buộc RDS.

RESTORE record do F06 phê duyệt phải bổ sung `source_allocated_storage_gb` là integer lấy từ metadata snapshot đã kiểm chứng owner/account/region. Config `db_storage_gb` của môi trường mới phải bằng dung lượng snapshot hoặc lớn hơn ít nhất 10%; không vượt giới hạn catalog 100 GiB. Thiếu metadata, thu nhỏ hoặc tăng quá ít bị từ chối. F03 dự toán/reserve theo dung lượng đích, không dùng mặc định 20 GiB cho một snapshot lớn hơn.

Ví dụ snapshot 40 GiB: restore 40 hoặc 44 GiB được chấp nhận; 20 và 41 GiB bị từ chối. Sau restore 40 GiB, preview update lên 44 GiB truyền AllocatedStorage=44 và giữ snapshot ID. Các update RDS cũng yêu cầu tăng ít nhất 10%, không hỗ trợ thu nhỏ. Change set vẫn phải qua preview/xác nhận và không được replacement DB.

Nguồn: [Restore từ snapshot](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_RestoreFromSnapshot.html), [RestoreDBInstanceFromDBSnapshot — AllocatedStorage](https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_RestoreDBInstanceFromDBSnapshot.html).

Có kiểm thử hồi quy và lint/validate template. Chưa chứng minh restore, tăng dung lượng hoặc dữ liệu ứng dụng trên DB thật; A22 phải đối chiếu DescribeDBInstances.AllocatedStorage với config và dữ liệu trước/sau thao tác. RDS còn có thời gian tối ưu hóa/cửa sổ cho lần tăng tiếp theo; không hứa thao tác hoàn tất tức thời.

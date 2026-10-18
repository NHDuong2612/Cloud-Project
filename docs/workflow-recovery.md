# Phục hồi workflow khi có lỗi

NEEDS_ATTENTION/FAILED giữ lock_owner và version hiện tại. Worker không mở khóa khi CloudFormation còn chạy hoặc rollback chưa được xác minh. Mất khóa có thể khiến thành viên khác hiểu nhầm rằng được phép chạy thao tác tiếp theo. F08/admin phải đối chiếu tài nguyên, trạng thái AWS và dữ liệu trước khi chuyển trạng thái hoặc bỏ khóa bằng transaction có điều kiện.

- Tạo mới thất bại: chỉ rollback stack có ownership tag đúng; chờ xóa tối đa 30 phút. Hết thời gian vẫn giữ khóa, inventory và NEEDS_ATTENTION, không tự tuyên bố sạch/hoàn quota.
- Update thất bại: không xóa stack nguồn; giữ khóa ngay cả khi AWS đang UPDATE_IN_PROGRESS/rollback. Đối chiếu cấu hình thực tế sau rollback trước khi thử tiếp.
- Gia hạn thất bại sau khi lấy khóa: không gọi CloudFormation hoặc cộng thêm giờ trong recover. Kiểm tra transaction SUCCEEDED/hạn mới đã ghi hay chưa trước khi phục hồi; gửi lại operation đã hoàn tất là no-op.
- Execution bị dừng/hết hạn: reconcile kiểm tra status/stateMachineArn bằng DescribeExecution, ghi lỗi đã lọc và giữ khóa. Sự kiện trùng hoặc sự kiện lỗi cũ không ghi đè execution đã thành công.
- Nếu Lambda đã commit trạng thái rồi mất phản hồi: lần thử lại đọc DynamoDB và không cộng giờ, execute change set hoặc tạo tác vụ lần nữa. Token/name cố định để đối chiếu tác vụ AWS.

Trong tests/asl_runner.py có bộ chạy cục bộ cho chính các Task/Choice/Wait/Retry/Catch hiện dùng trong deploy.asl.json, thời gian ảo và worker mới mỗi invocation. Các kiểm thử gồm tạo/health/READY, response loss ở create change set và execute, response loss sau commit gia hạn, retry hết giới hạn, rollback, deadline, execution bị dừng và sự kiện trùng/cũ. Đây không phải trình giả lập Step Functions đầy đủ; API validate ASL và bài chạy AWS thật vẫn cần thiết. Mock và SDK Stubber không kiểm tra được thực thi điều kiện DynamoDB hoặc IAM trên dịch vụ thật.

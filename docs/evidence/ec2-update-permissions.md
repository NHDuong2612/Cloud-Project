# Quyền đổi cấu hình EC2 — 19/10/2026

Đối chiếu Schema từ CloudFormation DescribeType cho AWS::EC2::Instance trong ap-southeast-1 cho thấy update handler dùng StopInstances/StartInstances; create/update cũng có ModifyInstanceCreditSpecification. Role deployer đã bổ sung các quyền này, giới hạn account/region, instance và tag Project=CloudHub. Read handler có DescribeAssociation/ListAssociations; bổ sung quyền chỉ đọc trong region.

Có kiểm thử hồi quy phạm vi IAM và Terraform validate. Chưa chạy thay loại instance trên AWS; kết quả kiểm tra mã không chứng minh mọi nhánh IAM của resource provider đã hoạt động. Không cấp toàn bộ danh sách quyền provider nếu thuộc tính tương ứng chưa được CloudHub hỗ trợ.

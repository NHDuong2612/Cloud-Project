output "control_table_name" { value = aws_dynamodb_table.control.name }
output "control_table_arn" { value = aws_dynamodb_table.control.arn }
output "control_stream_arn" { value = aws_dynamodb_table.control.stream_arn }
output "artifact_bucket_name" { value = aws_s3_bucket.artifacts.id }
output "approved_image_repository" { value = aws_ecr_repository.approved_apps.repository_url }
output "cloudformation_role_arn" { value = aws_iam_role.cloudformation.arn }
output "workload_boundary_arn" { value = aws_iam_policy.workload_boundary.arn }

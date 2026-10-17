output "control_table_name" { value = aws_dynamodb_table.control.name }
output "artifact_bucket_name" { value = aws_s3_bucket.artifacts.id }
output "cloudformation_role_arn" { value = aws_iam_role.cloudformation.arn }
output "workload_boundary_arn" { value = aws_iam_policy.workload_boundary.arn }

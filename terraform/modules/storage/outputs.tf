output "bucket_name" {
  value = var.enable_storage ? aws_s3_bucket.recovery[0].id : null
}

output "bucket_arn" {
  value = var.enable_storage ? aws_s3_bucket.recovery[0].arn : null
}

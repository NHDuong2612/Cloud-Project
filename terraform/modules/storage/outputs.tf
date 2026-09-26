output "bucket_name" {
  description = "Backup bucket name (null until enable_storage)"
  value       = var.enable_storage ? aws_s3_bucket.backups[0].id : null
}

output "bucket_arn" {
  description = "Backup bucket ARN"
  value       = var.enable_storage ? aws_s3_bucket.backups[0].arn : null
}

output "bucket_region" {
  description = "Bucket region"
  value       = var.enable_storage ? aws_s3_bucket.backups[0].region : null
}

output "versioning_status" {
  description = "S3 versioning status"
  value       = var.enable_storage ? aws_s3_bucket_versioning.backups[0].versioning_configuration[0].status : null
}

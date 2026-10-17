output "db_identifier" {
  description = "Human-readable RDS DB instance identifier"
  value       = var.enable_database ? aws_db_instance.postgres[0].identifier : null
}

output "db_endpoint" {
  description = "Private RDS endpoint host:port (VPC DNS)"
  value       = var.enable_database ? aws_db_instance.postgres[0].endpoint : null
  sensitive   = true
}

output "db_address" {
  description = "Private hostname only"
  value       = var.enable_database ? aws_db_instance.postgres[0].address : null
  sensitive   = true
}

output "db_port" {
  value = var.enable_database ? aws_db_instance.postgres[0].port : 5432
}

output "db_name" {
  value = var.enable_database ? aws_db_instance.postgres[0].db_name : null
}

output "db_username" {
  value = var.enable_database ? aws_db_instance.postgres[0].username : null
}

output "db_resource_id" {
  value = var.enable_database ? aws_db_instance.postgres[0].resource_id : null
}

output "master_user_secret_arn" {
  description = "Secrets Manager ARN for master password (AWS-managed)"
  value       = var.enable_database ? try(aws_db_instance.postgres[0].master_user_secret[0].secret_arn, null) : null
  sensitive   = true
}

output "publicly_accessible" {
  value = var.enable_database ? aws_db_instance.postgres[0].publicly_accessible : null
}

output "db_subnet_group_name" {
  value = var.enable_database ? aws_db_subnet_group.this[0].name : null
}

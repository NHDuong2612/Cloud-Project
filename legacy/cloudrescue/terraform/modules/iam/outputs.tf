output "controller_security_group_id" {
  description = "Controller SG ID (null until enable_iam)"
  value       = var.enable_iam ? aws_security_group.controller[0].id : null
}

output "target_security_group_id" {
  description = "Target SG ID"
  value       = var.enable_iam ? aws_security_group.target[0].id : null
}

output "database_security_group_id" {
  description = "Database SG ID — attach to RDS; 5432 not open to Internet"
  value       = var.enable_iam ? aws_security_group.database[0].id : null
}

output "controller_security_group_name" {
  value = var.enable_iam ? aws_security_group.controller[0].name : null
}

output "target_security_group_name" {
  value = var.enable_iam ? aws_security_group.target[0].name : null
}

output "database_security_group_name" {
  value = var.enable_iam ? aws_security_group.database[0].name : null
}

output "controller_role_arn" {
  value = var.enable_iam ? aws_iam_role.controller[0].arn : null
}

output "controller_instance_profile_name" {
  value = var.enable_iam ? aws_iam_instance_profile.controller[0].name : null
}

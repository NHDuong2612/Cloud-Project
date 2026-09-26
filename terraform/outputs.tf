# Handoff outputs for Người 3 — populated as modules are enabled.

output "name_prefix" {
  description = "Standard name prefix: cloudrescue-dev"
  value       = local.name_prefix
}

output "common_tags" {
  description = "Tags applied via provider default_tags / module resources"
  value       = local.common_tags
}

# --- Network (Task 5) ---
output "vpc_id" {
  value = module.network.vpc_id
}

output "vpc_cidr_block" {
  value = module.network.vpc_cidr_block
}

output "public_subnet_id" {
  value = module.network.public_subnet_id
}

output "public_subnet_az" {
  value = module.network.public_subnet_az
}

output "private_db_subnet_ids" {
  value = module.network.private_db_subnet_ids
}

output "private_db_subnet_azs" {
  value = module.network.private_db_subnet_azs
}

output "igw_id" {
  value = module.network.igw_id
}

output "availability_zones_used" {
  value = module.network.availability_zones_used
}

# --- Security Groups (Task 6) ---
output "controller_security_group_id" {
  value = module.iam.controller_security_group_id
}

output "target_security_group_id" {
  value = module.iam.target_security_group_id
}

output "database_security_group_id" {
  value = module.iam.database_security_group_id
}

output "controller_security_group_name" {
  value = module.iam.controller_security_group_name
}

output "target_security_group_name" {
  value = module.iam.target_security_group_name
}

output "database_security_group_name" {
  value = module.iam.database_security_group_name
}

output "controller_instance_profile_name" {
  value = module.iam.controller_instance_profile_name
}

output "controller_role_arn" {
  value = module.iam.controller_role_arn
}

# --- Storage (Task 7) ---
output "backup_bucket_name" {
  value = module.storage.bucket_name
}

output "backup_bucket_arn" {
  value = module.storage.bucket_arn
}

output "backup_bucket_region" {
  value = module.storage.bucket_region
}

output "backup_bucket_versioning" {
  value = module.storage.versioning_status
}

# --- Database (Task 8) ---
output "rds_identifier" {
  value = module.database.db_identifier
}

output "rds_endpoint" {
  description = "Private endpoint host:port (sensitive)"
  value       = module.database.db_endpoint
  sensitive   = true
}

output "rds_address" {
  value     = module.database.db_address
  sensitive = true
}

output "rds_port" {
  value = module.database.db_port
}

output "rds_publicly_accessible" {
  value = module.database.publicly_accessible
}

output "rds_subnet_group_name" {
  value = module.database.db_subnet_group_name
}

output "rds_master_user_secret_arn" {
  value     = module.database.master_user_secret_arn
  sensitive = true
}

# --- Controller (Task 8 connectivity) ---
output "controller_instance_id" {
  value = module.controller.instance_id
}

output "controller_private_ip" {
  value = module.controller.private_ip
}

output "controller_public_ip" {
  value = module.controller.public_ip
}

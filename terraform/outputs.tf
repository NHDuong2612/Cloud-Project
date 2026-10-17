output "name_prefix" {
  value = local.name_prefix
}

output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "private_db_subnet_ids" {
  value = module.network.private_db_subnet_ids
}

output "recovery_bucket_name" {
  value = module.storage.bucket_name
}

output "recovery_bucket_arn" {
  value = module.storage.bucket_arn
}

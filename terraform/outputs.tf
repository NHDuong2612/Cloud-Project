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

output "platform" {
  value = var.enable_platform ? {
    control_table_name      = module.platform[0].control_table_name
    artifact_bucket_name    = module.platform[0].artifact_bucket_name
    cloudformation_role_arn = module.platform[0].cloudformation_role_arn
    workload_boundary_arn   = module.platform[0].workload_boundary_arn
  } : null
}

output "deployment_workflow" {
  value = var.enable_orchestrator && var.enable_platform ? {
    state_machine_arn      = module.orchestrator[0].state_machine_arn
    start_execution_policy = module.orchestrator[0].start_execution_policy
    control_stream_arn     = module.platform[0].control_stream_arn
    failures_queue_arn     = module.orchestrator[0].failures_queue_arn
  } : null
}

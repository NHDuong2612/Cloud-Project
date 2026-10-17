module "network" {
  source = "./modules/network"

  enable_network          = var.enable_network
  project_name            = var.project_name
  environment             = var.environment
  common_tags             = local.common_tags
  vpc_cidr                = var.vpc_cidr
  public_subnet_cidrs     = var.public_subnet_cidrs
  private_db_subnet_cidrs = var.private_db_subnet_cidrs
  availability_zones      = var.availability_zones
}

module "storage" {
  source = "./modules/storage"

  enable_storage = var.enable_storage
  project_name   = var.project_name
  environment    = var.environment
  common_tags    = local.common_tags
}

module "platform" {
  source = "./modules/platform"

  count                   = var.enable_platform ? 1 : 0
  name_prefix             = local.name_prefix
  common_tags             = local.common_tags
  recovery_bucket_arn     = module.storage.bucket_arn
  allowed_hosted_zone_ids = var.allowed_hosted_zone_ids
  allowed_base_domain     = var.allowed_base_domain
}

resource "terraform_data" "orchestrator_configuration" {
  lifecycle {
    precondition {
      condition     = length(var.allowed_hosted_zone_ids) == 0 || var.allowed_base_domain != ""
      error_message = "DNS permissions require an allowed base domain."
    }
    precondition {
      condition     = !var.enable_orchestrator || (var.enable_platform && can(regex("^worker/[a-f0-9]{64}\\.zip$", var.worker_s3_key)))
      error_message = "Orchestrator requires enable_platform and an immutable worker/<sha256>.zip key."
    }
  }
}

module "orchestrator" {
  source             = "./modules/orchestrator"
  count              = var.enable_orchestrator && var.enable_platform ? 1 : 0
  name_prefix        = local.name_prefix
  common_tags        = local.common_tags
  control_table_name = module.platform[0].control_table_name
  control_table_arn  = module.platform[0].control_table_arn
  artifact_bucket    = module.platform[0].artifact_bucket_name
  worker_s3_key      = var.worker_s3_key
  cfn_role_arn       = module.platform[0].cloudformation_role_arn
  verified_templates = var.verified_templates
  approved_images    = var.approved_images
  platform_parameters = merge(var.platform_parameters, var.enable_network ? {
    VpcId            = module.network.vpc_id
    PublicSubnetId   = module.network.public_subnet_ids[0]
    PublicSubnetIds  = join(",", module.network.public_subnet_ids)
    PrivateSubnetIds = join(",", module.network.private_db_subnet_ids)
    } : {}, {
    WorkloadBoundaryArn = module.platform[0].workload_boundary_arn
    CodeBucket          = module.platform[0].artifact_bucket_name
    RecoveryBucketName  = coalesce(module.storage.bucket_name, "unconfigured")
  })
  depends_on = [terraform_data.orchestrator_configuration]
}

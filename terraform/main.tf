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

  count               = var.enable_platform ? 1 : 0
  name_prefix         = local.name_prefix
  common_tags         = local.common_tags
  recovery_bucket_arn = module.storage.bucket_arn
}

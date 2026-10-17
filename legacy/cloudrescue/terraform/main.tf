# =============================================================================
# CloudRescue — Terraform root (environment: wire modules here)
# Phase 1: skeleton only — no costly AWS resources yet.
# =============================================================================

# Network: VPC, subnets, IGW, route tables (Phase 2)
module "network" {
  source = "./modules/network"

  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  vpc_cidr                = var.vpc_cidr
  public_subnet_cidr      = var.public_subnet_cidr
  private_db_subnet_cidrs = var.private_db_subnet_cidrs
  availability_zones      = var.availability_zones

  # Phase 1: keep false so `terraform plan` creates nothing expensive.
  # Phase 2: set enable_network = true in terraform.tfvars
  enable_network = var.enable_network
}

# Storage: S3 backup bucket (Phase 4)
module "storage" {
  source = "./modules/storage"

  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags
  aws_region   = var.aws_region

  enable_storage                     = var.enable_storage
  noncurrent_version_expiration_days = var.s3_noncurrent_version_expiration_days
}

# IAM + Security Groups (Phase 3)
# Depends on: network.vpc_id (for SGs). S3 policy uses storage.bucket_arn (Phase 4).
module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  vpc_id            = module.network.vpc_id
  backup_bucket_arn = module.storage.bucket_arn
  ssh_ingress_cidr  = var.ssh_ingress_cidr

  enable_iam = var.enable_iam
}

# Database: RDS PostgreSQL in private subnets (Phase 5)
module "database" {
  source = "./modules/database"

  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  private_subnet_ids   = module.network.private_db_subnet_ids
  db_security_group_id = module.iam.database_security_group_id

  db_name                 = var.db_name
  db_username             = var.db_username
  db_instance_class       = var.db_instance_class
  db_engine_version       = var.db_engine_version
  db_allocated_storage    = var.db_allocated_storage
  db_availability_zone    = var.db_availability_zone
  backup_retention_period = var.db_backup_retention_period

  # Unused when AWS manages master password via Secrets Manager
  db_password = var.db_password

  enable_database = var.enable_database
}

# Controller EC2 + (later) target wiring hooks (Phase 3+ / Người 3)
module "controller" {
  source = "./modules/controller"

  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  public_subnet_id             = module.network.public_subnet_id
  controller_security_group_id = module.iam.controller_security_group_id
  instance_profile_name        = module.iam.controller_instance_profile_name
  instance_type                = var.controller_instance_type

  enable_controller = var.enable_controller
}

# Observability placeholders: CloudWatch logs/alarms (optional later)
module "observability" {
  source = "./modules/observability"

  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  enable_observability = var.enable_observability
}

# -----------------------------------------------------------------------------
# Core identity / naming (align with docs/aws-convention.md)
# -----------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region for all CloudRescue resources (group must use one region)."
  type        = string
  # Example: ap-southeast-1 — set in terraform.tfvars (do not commit secrets there)
}

variable "aws_profile" {
  description = "Optional local AWS CLI profile name (prefer AWS_PROFILE env instead)."
  type        = string
  default     = "cloudrescue-dev"
}

variable "project_name" {
  description = "Short project slug used in resource names (lowercase)."
  type        = string
  default     = "cloudrescue"
}

variable "environment" {
  description = "Deployment environment: dev | staging | prod"
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Owner tag value, e.g. nhom01-person2"
  type        = string
}

variable "job_id" {
  description = "JobId tag; use none for shared infra"
  type        = string
  default     = "none"
}

variable "mode" {
  description = "Mode tag: shared | drill | manual"
  type        = string
  default     = "shared"
}

variable "expires_at" {
  description = "ISO date when temporary resources should be cleaned up"
  type        = string
  # Example: 2026-12-31
}

# -----------------------------------------------------------------------------
# Feature flags — enable modules phase by phase (cost control)
# -----------------------------------------------------------------------------

variable "enable_network" {
  description = "Phase 2: create VPC / subnets / routing"
  type        = bool
  default     = false
}

variable "enable_iam" {
  description = "Task 6: security groups; Task 9: IAM roles/profiles"
  type        = bool
  default     = false
}

variable "ssh_ingress_cidr" {
  description = "Optional operator CIDR for SSH to controller (e.g. 1.2.3.4/32). Leave empty to disable Internet SSH."
  type        = string
  default     = ""
}

variable "enable_storage" {
  description = "Task 7: create S3 backup bucket"
  type        = bool
  default     = false
}

variable "s3_noncurrent_version_expiration_days" {
  description = "Expire noncurrent S3 versions under backups/ after N days"
  type        = number
  default     = 30
}

variable "enable_database" {
  description = "Phase 5: create RDS PostgreSQL (COSTS MONEY while running)"
  type        = bool
  default     = false
}

variable "enable_controller" {
  description = "Later: create controller EC2 (COSTS MONEY while running)"
  type        = bool
  default     = false
}

variable "enable_observability" {
  description = "Optional: CloudWatch log groups / basic alarms"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# Network (used when enable_network = true)
# -----------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR for CloudRescue VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Public subnet CIDR (controller / target)"
  type        = string
  default     = "10.20.1.0/24"
}

variable "private_db_subnet_cidrs" {
  description = "Two private DB subnet CIDRs in two AZs (RDS requirement)"
  type        = list(string)
  default     = ["10.20.10.0/24", "10.20.11.0/24"]
}

variable "availability_zones" {
  description = "Exactly two AZs for DB subnets (and public subnet uses index 0)"
  type        = list(string)
  default     = [] # empty => module derives from data.aws_availability_zones
}

# -----------------------------------------------------------------------------
# Database (used when enable_database = true) — never commit real password
# -----------------------------------------------------------------------------

variable "db_name" {
  description = "Initial PostgreSQL database name"
  type        = string
  default     = "cloudrescue"
}

variable "db_username" {
  description = "Master username for RDS (not a secret by itself, but keep out of git if policy requires)"
  type        = string
  default     = "cr_admin"
}

variable "db_password" {
  description = "Master password for RDS. Set via TF_VAR_db_password or terraform.tfvars (gitignored)."
  type        = string
  sensitive   = true
  default     = null
}

variable "db_instance_class" {
  description = "Small instance for student demo"
  type        = string
  default     = "db.t3.micro"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version major"
  type        = string
  default     = "16"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_availability_zone" {
  description = "Pin Single-AZ (null = AWS chooses)"
  type        = string
  default     = null
}

variable "db_backup_retention_period" {
  type    = number
  default = 1
}

# -----------------------------------------------------------------------------
# Controller (Task 8 connectivity + Task 9 SSM)
# -----------------------------------------------------------------------------

variable "controller_instance_type" {
  description = "EC2 instance type for controller"
  type        = string
  default     = "t3.micro"
}

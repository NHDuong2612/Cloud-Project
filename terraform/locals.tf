locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = "CloudHub"
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
    Scope       = "shared-platform"
  }
}

# Shared naming + tags for all modules (matches docs/aws-convention.md)

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = "CloudRescue"
    Environment = var.environment
    Owner       = var.owner
    JobId       = var.job_id
    Mode        = var.mode
    ExpiresAt   = var.expires_at
    ManagedBy   = "terraform"
  }
}

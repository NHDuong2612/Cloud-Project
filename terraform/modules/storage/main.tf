# Private, versioned CloudHub bucket for recovery artifacts and manifests.
# The per-session retention policy is implemented by CloudHub's lifecycle jobs.

data "aws_caller_identity" "current" {
  count = var.enable_storage ? 1 : 0
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  bucket_name = var.enable_storage ? "${local.name_prefix}-recovery-${data.aws_caller_identity.current[0].account_id}" : null
}

resource "aws_s3_bucket" "recovery" {
  count  = var.enable_storage ? 1 : 0
  bucket = local.bucket_name

  tags = merge(var.common_tags, {
    Name    = local.bucket_name
    Purpose = "cloudhub-recovery-artifacts"
  })
}

resource "aws_s3_bucket_public_access_block" "recovery" {
  count  = var.enable_storage ? 1 : 0
  bucket = aws_s3_bucket.recovery[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "recovery" {
  count  = var.enable_storage ? 1 : 0
  bucket = aws_s3_bucket.recovery[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "recovery" {
  count  = var.enable_storage ? 1 : 0
  bucket = aws_s3_bucket.recovery[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_ownership_controls" "recovery" {
  count  = var.enable_storage ? 1 : 0
  bucket = aws_s3_bucket.recovery[0].id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "recovery" {
  count  = var.enable_storage ? 1 : 0
  bucket = aws_s3_bucket.recovery[0].id

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

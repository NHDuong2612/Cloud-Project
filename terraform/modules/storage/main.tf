# Module: storage — Task 7: private S3 backup vault (OpenStack -> AWS)
#
# Prefixed layout (for Người 1 / Người 3 backup jobs):
#   s3://<bucket>/backups/<job-id>/database/
#   s3://<bucket>/backups/<job-id>/uploads/
#   s3://<bucket>/backups/<job-id>/manifest.json
#   s3://<bucket>/metadata/
#   s3://<bucket>/manifests/
#
# Cost: empty/demo objects are cents; prefer SSE-S3 (AES256) over KMS to avoid key fees.

data "aws_caller_identity" "current" {
  count = var.enable_storage ? 1 : 0
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  # Globally unique bucket name
  bucket_name = var.enable_storage ? "${local.name_prefix}-backups-${data.aws_caller_identity.current[0].account_id}" : null
}

resource "aws_s3_bucket" "backups" {
  count = var.enable_storage ? 1 : 0

  bucket = local.bucket_name

  tags = merge(var.common_tags, {
    Name    = local.bucket_name
    Purpose = "openstack-to-aws-backups"
  })
}

# Block all public access (required for demo security)
resource "aws_s3_bucket_public_access_block" "backups" {
  count = var.enable_storage ? 1 : 0

  bucket = aws_s3_bucket.backups[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# SSE-S3 (AES256) — encrypted at rest, no customer-managed KMS cost
resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  count = var.enable_storage ? 1 : 0

  bucket = aws_s3_bucket.backups[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Versioning — keep previous backup object versions (prove restore integrity / rollback)
resource "aws_s3_bucket_versioning" "backups" {
  count = var.enable_storage ? 1 : 0

  bucket = aws_s3_bucket.backups[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

# Ownership: BucketOwnerEnforced (ACLs disabled — modern default)
resource "aws_s3_bucket_ownership_controls" "backups" {
  count = var.enable_storage ? 1 : 0

  bucket = aws_s3_bucket.backups[0].id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Lifecycle: expire old noncurrent versions to control cost on student accounts
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  count = var.enable_storage ? 1 : 0

  bucket = aws_s3_bucket.backups[0].id

  depends_on = [aws_s3_bucket_versioning.backups]

  rule {
    id     = "expire-noncurrent-backup-versions"
    status = "Enabled"

    filter {
      prefix = "backups/"
    }

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expiration_days
    }
  }

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Prefix markers so the backup layout is visible in Console (zero-byte objects)
resource "aws_s3_object" "prefix_backups" {
  count = var.enable_storage ? 1 : 0

  bucket       = aws_s3_bucket.backups[0].id
  key          = "backups/"
  content_type = "application/x-directory"
  content      = ""
}

resource "aws_s3_object" "prefix_metadata" {
  count = var.enable_storage ? 1 : 0

  bucket       = aws_s3_bucket.backups[0].id
  key          = "metadata/"
  content_type = "application/x-directory"
  content      = ""
}

resource "aws_s3_object" "prefix_manifests" {
  count = var.enable_storage ? 1 : 0

  bucket       = aws_s3_bucket.backups[0].id
  key          = "manifests/"
  content_type = "application/x-directory"
  content      = ""
}

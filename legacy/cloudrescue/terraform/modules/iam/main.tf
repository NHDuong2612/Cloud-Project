# Module: iam — Task 6 security groups + Task 9 controller IAM role/profile
#
# RDS "not public" is enforced by:
# 1) database SG — TCP 5432 ONLY from controller-sg + target-sg (never 0.0.0.0/0)
# 2) private subnets (Task 5) + publicly_accessible = false (Task 8)

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# -----------------------------------------------------------------------------
# 1) Controller SG — recovery orchestrator (public subnet later)
# -----------------------------------------------------------------------------
# Inbound: only from target (peer traffic). No SSH from the whole Internet.
# Outbound: all — needed for S3 / SSM / package APIs without NAT/VPC endpoints.

resource "aws_security_group" "controller" {
  count = var.enable_iam ? 1 : 0

  name        = "${local.name_prefix}-sg-controller"
  description = "CloudRescue controller EC2 - orchestrates backup restore drill"
  vpc_id      = var.vpc_id

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-sg-controller"
    Role = "controller"
  })

  lifecycle {
    precondition {
      condition     = var.vpc_id != null && var.vpc_id != ""
      error_message = "enable_iam=true requires vpc_id from network (enable_network=true and apply first)."
    }
  }
}

resource "aws_security_group_rule" "controller_egress_all" {
  count = var.enable_iam ? 1 : 0

  type              = "egress"
  security_group_id = aws_security_group.controller[0].id
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow outbound to AWS APIs (S3, SSM) and package mirrors"
}

# Optional SSH only if you set ssh_ingress_cidr (e.g. your home IP/32). Empty = no SSH.
resource "aws_security_group_rule" "controller_ingress_ssh" {
  count = var.enable_iam && var.ssh_ingress_cidr != null && var.ssh_ingress_cidr != "" ? 1 : 0

  type              = "ingress"
  security_group_id = aws_security_group.controller[0].id
  protocol          = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = [var.ssh_ingress_cidr]
  description       = "Optional SSH from operator CIDR only (prefer SSM)"
}

resource "aws_security_group_rule" "controller_ingress_from_target" {
  count = var.enable_iam ? 1 : 0

  type                     = "ingress"
  security_group_id        = aws_security_group.controller[0].id
  protocol                 = "tcp"
  from_port                = 0
  to_port                  = 65535
  source_security_group_id = aws_security_group.target[0].id
  description              = "Allow TCP from target during restore/validation"
}

# -----------------------------------------------------------------------------
# 2) Target SG — recovery application host (public subnet later)
# -----------------------------------------------------------------------------
# Inbound: only from controller (app + admin ports). Not open to 0.0.0.0/0.
# Outbound: all — app may call RDS (via SG) and HTTPS.

resource "aws_security_group" "target" {
  count = var.enable_iam ? 1 : 0

  name        = "${local.name_prefix}-sg-target"
  description = "CloudRescue target EC2 - restored application environment"
  vpc_id      = var.vpc_id

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-sg-target"
    Role = "target"
  })
}

resource "aws_security_group_rule" "target_egress_all" {
  count = var.enable_iam ? 1 : 0

  type              = "egress"
  security_group_id = aws_security_group.target[0].id
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow outbound (RDS in VPC + HTTPS)"
}

resource "aws_security_group_rule" "target_ingress_ssh_from_controller" {
  count = var.enable_iam ? 1 : 0

  type                     = "ingress"
  security_group_id        = aws_security_group.target[0].id
  protocol                 = "tcp"
  from_port                = 22
  to_port                  = 22
  source_security_group_id = aws_security_group.controller[0].id
  description              = "SSH from controller only (not Internet)"
}

resource "aws_security_group_rule" "target_ingress_http_from_controller" {
  count = var.enable_iam ? 1 : 0

  type                     = "ingress"
  security_group_id        = aws_security_group.target[0].id
  protocol                 = "tcp"
  from_port                = 80
  to_port                  = 80
  source_security_group_id = aws_security_group.controller[0].id
  description              = "HTTP health/check from controller"
}

resource "aws_security_group_rule" "target_ingress_https_from_controller" {
  count = var.enable_iam ? 1 : 0

  type                     = "ingress"
  security_group_id        = aws_security_group.target[0].id
  protocol                 = "tcp"
  from_port                = 443
  to_port                  = 443
  source_security_group_id = aws_security_group.controller[0].id
  description              = "HTTPS from controller"
}

resource "aws_security_group_rule" "target_ingress_app_from_controller" {
  count = var.enable_iam ? 1 : 0

  type                     = "ingress"
  security_group_id        = aws_security_group.target[0].id
  protocol                 = "tcp"
  from_port                = 8000
  to_port                  = 8000
  source_security_group_id = aws_security_group.controller[0].id
  description              = "App port (EquipmentDesk-style) from controller"
}

# -----------------------------------------------------------------------------
# 3) Database SG — RDS PostgreSQL (private subnets; NEVER public)
# -----------------------------------------------------------------------------
# Inbound: 5432 ONLY from controller-sg and target-sg.
# NO cidr_blocks = ["0.0.0.0/0"] on 5432.

resource "aws_security_group" "database" {
  count = var.enable_iam ? 1 : 0

  name        = "${local.name_prefix}-sg-database"
  description = "CloudRescue RDS PostgreSQL - private; 5432 from controller/target only"
  vpc_id      = var.vpc_id

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-sg-database"
    Role = "database"
  })
}

resource "aws_security_group_rule" "database_ingress_postgres_from_controller" {
  count = var.enable_iam ? 1 : 0

  type                     = "ingress"
  security_group_id        = aws_security_group.database[0].id
  protocol                 = "tcp"
  from_port                = 5432
  to_port                  = 5432
  source_security_group_id = aws_security_group.controller[0].id
  description              = "PostgreSQL from controller only"
}

resource "aws_security_group_rule" "database_ingress_postgres_from_target" {
  count = var.enable_iam ? 1 : 0

  type                     = "ingress"
  security_group_id        = aws_security_group.database[0].id
  protocol                 = "tcp"
  from_port                = 5432
  to_port                  = 5432
  source_security_group_id = aws_security_group.target[0].id
  description              = "PostgreSQL from target app only"
}

# RDS rarely needs Internet; keep egress open for AWS-managed needs (patches via AWS network).
resource "aws_security_group_rule" "database_egress_all" {
  count = var.enable_iam ? 1 : 0

  type              = "egress"
  security_group_id = aws_security_group.database[0].id
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Default egress for managed RDS operations"
}

# -----------------------------------------------------------------------------
# Task 9: Controller IAM role + instance profile (no access keys on EC2)
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "controller_assume" {
  count = var.enable_iam ? 1 : 0

  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "controller" {
  count = var.enable_iam ? 1 : 0

  name               = "${local.name_prefix}-role-controller"
  assume_role_policy = data.aws_iam_policy_document.controller_assume[0].json

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-role-controller"
    Role = "controller"
  })
}

# SSM Session Manager / Run Command (no inbound SSH required)
resource "aws_iam_role_policy_attachment" "controller_ssm" {
  count = var.enable_iam ? 1 : 0

  role       = aws_iam_role.controller[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "controller_app" {
  count = var.enable_iam ? 1 : 0

  # S3 backup bucket (OpenStack -> AWS backups)
  dynamic "statement" {
    for_each = var.backup_bucket_arn != null && var.backup_bucket_arn != "" ? [1] : []
    content {
      sid    = "S3BackupBucket"
      effect = "Allow"
      actions = [
        "s3:ListBucket",
        "s3:GetBucketLocation",
      ]
      resources = [var.backup_bucket_arn]
    }
  }

  dynamic "statement" {
    for_each = var.backup_bucket_arn != null && var.backup_bucket_arn != "" ? [1] : []
    content {
      sid    = "S3BackupObjects"
      effect = "Allow"
      actions = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListMultipartUploadParts",
        "s3:AbortMultipartUpload",
      ]
      resources = ["${var.backup_bucket_arn}/*"]
    }
  }

  # Read RDS-managed master password secret (for private connectivity tests)
  statement {
    sid    = "ReadRdsMasterSecret"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = ["arn:aws:secretsmanager:*:*:secret:rds!*"]
  }
}

resource "aws_iam_role_policy" "controller_app" {
  count = var.enable_iam ? 1 : 0

  name   = "${local.name_prefix}-policy-controller-app"
  role   = aws_iam_role.controller[0].id
  policy = data.aws_iam_policy_document.controller_app[0].json
}

resource "aws_iam_instance_profile" "controller" {
  count = var.enable_iam ? 1 : 0

  name = "${local.name_prefix}-profile-controller"
  role = aws_iam_role.controller[0].name

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-profile-controller"
  })
}

# Module: database — Task 8: RDS PostgreSQL (small, Single-AZ, private)
#
# Cost warning: db.t3.micro + 20GB gp3 charges while the instance is Available.
# Stop/delete after demo. No Multi-AZ. No public access.
#
# "Private endpoint" = RDS DNS endpoint resolvable inside the VPC only
# (publicly_accessible = false). Controller reaches it via private IP / DNS,
# allowed by database SG (5432 from controller-sg).

terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

resource "aws_db_subnet_group" "this" {
  count = var.enable_database ? 1 : 0

  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-db-subnet-group"
  })

  lifecycle {
    precondition {
      condition     = length(var.private_subnet_ids) >= 2
      error_message = "RDS needs at least 2 private subnet IDs in different AZs."
    }
    precondition {
      condition     = var.db_security_group_id != null && var.db_security_group_id != ""
      error_message = "db_security_group_id is required (enable_iam=true and apply SGs first)."
    }
  }
}

resource "aws_db_instance" "postgres" {
  count = var.enable_database ? 1 : 0

  identifier     = "${local.name_prefix}-rds"
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  allocated_storage = var.db_allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username

  # AWS-managed master password in Secrets Manager (no password in Git / tfvars)
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.this[0].name
  vpc_security_group_ids = [var.db_security_group_id]
  publicly_accessible    = false
  multi_az               = false
  availability_zone      = var.db_availability_zone

  backup_retention_period = var.backup_retention_period
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true

  # Demo-friendly: allow minor upgrades
  auto_minor_version_upgrade = true

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-rds"
    Role = "recovery-database"
  })
}

# Module: controller — EC2 recovery controller (public subnet + SSM + private path to RDS)
#
# Cost: t3.micro while running. Stop instance when not demoing.
# Public subnet + public IP (no NAT) so SSM agent can reach AWS APIs.
# RDS access uses private VPC DNS to the RDS endpoint (not the public Internet).

data "aws_ami" "al2023" {
  count = var.enable_controller ? 1 : 0

  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

resource "aws_instance" "controller" {
  count = var.enable_controller ? 1 : 0

  ami                         = data.aws_ami.al2023[0].id
  instance_type               = var.instance_type
  subnet_id                   = var.public_subnet_id
  vpc_security_group_ids      = [var.controller_security_group_id]
  iam_instance_profile        = var.instance_profile_name
  associate_public_ip_address = true

  # No SSH key required when using SSM Session Manager
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 30
    encrypted   = true
  }

  user_data = <<-EOF
              #!/bin/bash
              set -euo pipefail
              dnf install -y postgresql15
              EOF

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-controller"
    Role = "controller"
  })

  lifecycle {
    precondition {
      condition     = var.public_subnet_id != null && var.public_subnet_id != ""
      error_message = "public_subnet_id required (enable_network)."
    }
    precondition {
      condition     = var.controller_security_group_id != null && var.controller_security_group_id != ""
      error_message = "controller_security_group_id required (enable_iam)."
    }
    precondition {
      condition     = var.instance_profile_name != null && var.instance_profile_name != ""
      error_message = "instance_profile_name required (IAM profile)."
    }
  }
}

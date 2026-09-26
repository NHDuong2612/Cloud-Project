# Module: observability — CloudWatch placeholders (optional)

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# PLACEHOLDER: aws_cloudwatch_log_group for restore/validation job logs

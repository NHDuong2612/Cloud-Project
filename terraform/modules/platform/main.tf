data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_partition" "current" {}

locals {
  arn_prefix        = "arn:${data.aws_partition.current.partition}"
  account_id        = data.aws_caller_identity.current.account_id
  region            = data.aws_region.current.name
  workload_role_arn = "${local.arn_prefix}:iam::${local.account_id}:role/cloudhub/workloads/cloudhub-env-*"
}

resource "aws_dynamodb_table" "control" {
  name             = "${var.name_prefix}-control"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "pk"
  range_key        = "sk"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  point_in_time_recovery { enabled = true }
  server_side_encryption { enabled = true }
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  tags = var.common_tags
  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket" "artifacts" {
  bucket        = "${var.name_prefix}-deployment-${local.account_id}"
  force_destroy = false
  tags          = merge(var.common_tags, { Purpose = "trusted-deployment-code" })
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_policy" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Deny", Principal = "*", Action = "s3:*"
      Resource  = [aws_s3_bucket.artifacts.arn, "${aws_s3_bucket.artifacts.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}

# Every environment has its own role and inline policy. This boundary caps the
# authority of those roles even if a future template accidentally grants more.
resource "aws_iam_policy" "workload_boundary" {
  name = "${var.name_prefix}-workload-boundary"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      { Effect = "Allow", Action = ["ssm:UpdateInstanceInformation", "ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"], Resource = "*" },
      { Effect = "Allow", Action = ["s3:GetObject", "s3:GetObjectVersion"], Resource = "${aws_s3_bucket.artifacts.arn}/apps/*" },
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = "${local.arn_prefix}:secretsmanager:${local.region}:${local.account_id}:secret:rds!*" },
      { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
      { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"], Resource = "${local.arn_prefix}:ecr:${local.region}:${local.account_id}:repository/*" },
      { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${local.arn_prefix}:logs:${local.region}:${local.account_id}:log-group:/cloudhub/environments/*:*" }
      ], var.recovery_bucket_arn == null ? [] : [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = "${var.recovery_bucket_arn}/environments/*" }
    ])
  })
  tags = var.common_tags
}

resource "aws_iam_role" "cloudformation" {
  name = "${var.name_prefix}-environment-deployer"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "cloudformation.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
  tags = var.common_tags
}

resource "aws_iam_role_policy" "cloudformation" {
  role = aws_iam_role.cloudformation.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "EnvironmentServicesInRegion", Effect = "Allow", Resource = "*"
        Action = [
          "ec2:Describe*", "ec2:RunInstances", "ec2:TerminateInstances", "ec2:CreateTags", "ec2:DeleteTags", "ec2:CreateSecurityGroup", "ec2:DeleteSecurityGroup", "ec2:AuthorizeSecurityGroupIngress", "ec2:RevokeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress", "ec2:RevokeSecurityGroupEgress", "ec2:CreateLaunchTemplate", "ec2:CreateLaunchTemplateVersion", "ec2:DeleteLaunchTemplate", "ec2:DeleteLaunchTemplateVersions", "ec2:ModifyLaunchTemplate", "ec2:ModifyInstanceAttribute",
          "rds:CreateDBInstance", "rds:ModifyDBInstance", "rds:DeleteDBInstance", "rds:DescribeDBInstances", "rds:CreateDBSubnetGroup", "rds:ModifyDBSubnetGroup", "rds:DeleteDBSubnetGroup", "rds:DescribeDBSubnetGroups", "rds:AddTagsToResource", "rds:RemoveTagsFromResource", "rds:ListTagsForResource", "rds:CreateDBSnapshot", "rds:DescribeDBSnapshots", "rds:RestoreDBInstanceFromDBSnapshot", "rds:CreateDBParameterGroup", "rds:ModifyDBParameterGroup", "rds:DeleteDBParameterGroup", "rds:DescribeDBParameterGroups", "rds:DescribeDBParameters",
          "elasticloadbalancing:CreateLoadBalancer", "elasticloadbalancing:DeleteLoadBalancer", "elasticloadbalancing:CreateTargetGroup", "elasticloadbalancing:DeleteTargetGroup", "elasticloadbalancing:CreateListener", "elasticloadbalancing:DeleteListener", "elasticloadbalancing:ModifyListener", "elasticloadbalancing:ModifyLoadBalancerAttributes", "elasticloadbalancing:ModifyTargetGroup", "elasticloadbalancing:ModifyTargetGroupAttributes", "elasticloadbalancing:Describe*", "elasticloadbalancing:AddTags", "elasticloadbalancing:RemoveTags", "elasticloadbalancing:RegisterTargets", "elasticloadbalancing:DeregisterTargets", "elasticloadbalancing:SetSecurityGroups", "elasticloadbalancing:SetSubnets",
          "autoscaling:CreateAutoScalingGroup", "autoscaling:UpdateAutoScalingGroup", "autoscaling:DeleteAutoScalingGroup", "autoscaling:Describe*", "autoscaling:CreateOrUpdateTags", "autoscaling:DeleteTags", "autoscaling:PutScalingPolicy", "autoscaling:DeletePolicy", "autoscaling:SetDesiredCapacity",
          "ecs:CreateCluster", "ecs:DeleteCluster", "ecs:Describe*", "ecs:List*", "ecs:RegisterTaskDefinition", "ecs:DeregisterTaskDefinition", "ecs:CreateService", "ecs:UpdateService", "ecs:DeleteService", "ecs:TagResource", "ecs:UntagResource",
          "logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:PutRetentionPolicy", "logs:DescribeLogGroups", "logs:ListTagsForResource", "logs:TagResource", "logs:UntagResource", "cloudwatch:PutMetricAlarm", "cloudwatch:DeleteAlarms", "cloudwatch:DescribeAlarms"
        ]
        Condition = { StringEquals = { "aws:RequestedRegion" = local.region } }
      },
      {
        Sid       = "CreateBoundedWorkloadRoles", Effect = "Allow", Action = "iam:CreateRole", Resource = local.workload_role_arn
        Condition = { StringEquals = { "iam:PermissionsBoundary" = aws_iam_policy.workload_boundary.arn } }
      },
      { Effect = "Allow", Action = ["iam:GetRole", "iam:DeleteRole", "iam:PutRolePolicy", "iam:GetRolePolicy", "iam:DeleteRolePolicy", "iam:ListRolePolicies", "iam:TagRole", "iam:UntagRole"], Resource = local.workload_role_arn },
      { Effect = "Allow", Action = ["iam:CreateInstanceProfile", "iam:GetInstanceProfile", "iam:AddRoleToInstanceProfile", "iam:RemoveRoleFromInstanceProfile", "iam:DeleteInstanceProfile", "iam:TagInstanceProfile", "iam:UntagInstanceProfile"], Resource = "${local.arn_prefix}:iam::${local.account_id}:instance-profile/cloudhub/workloads/cloudhub-env-*" },
      { Effect = "Allow", Action = "iam:PassRole", Resource = local.workload_role_arn, Condition = { StringEquals = { "iam:PassedToService" = ["ec2.amazonaws.com", "ecs-tasks.amazonaws.com"] } } },
      { Effect = "Allow", Action = "iam:CreateServiceLinkedRole", Resource = "${local.arn_prefix}:iam::${local.account_id}:role/aws-service-role/*", Condition = { StringEquals = { "iam:AWSServiceName" = ["autoscaling.amazonaws.com", "rds.amazonaws.com", "ecs.amazonaws.com", "elasticloadbalancing.amazonaws.com"] } } },
      { Effect = "Allow", Action = ["secretsmanager:CreateSecret", "secretsmanager:TagResource", "secretsmanager:DescribeSecret"], Resource = "${local.arn_prefix}:secretsmanager:${local.region}:${local.account_id}:secret:rds!*" },
      { Effect = "Allow", Action = "ssm:GetParameters", Resource = "${local.arn_prefix}:ssm:${local.region}::parameter/aws/service/ami-amazon-linux-latest/*" }
    ]
  })
}

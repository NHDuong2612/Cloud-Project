data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}

locals {
  prefix       = "arn:${data.aws_partition.current.partition}"
  account      = data.aws_caller_identity.current.account_id
  region       = data.aws_region.current.name
  workflow_arn = "${local.prefix}:states:${local.region}:${local.account}:stateMachine:${var.name_prefix}-deployment"
  worker_env = {
    CONTROL_TABLE       = var.control_table_name
    CFN_ROLE_ARN        = var.cfn_role_arn
    PLATFORM_PARAMETERS = jsonencode(var.platform_parameters)
    VERIFIED_TEMPLATES  = join(",", var.verified_templates)
    APPROVED_IMAGES     = jsonencode(var.approved_images)
  }
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${var.name_prefix}-deployment-worker"
  retention_in_days = 14
  tags              = var.common_tags
}
resource "aws_cloudwatch_log_group" "reconcile" {
  name              = "/aws/lambda/${var.name_prefix}-deployment-reconcile"
  retention_in_days = 14
  tags              = var.common_tags
}
resource "aws_cloudwatch_log_group" "workflow" {
  name              = "/aws/vendedlogs/states/${var.name_prefix}-deployment"
  retention_in_days = 14
  tags              = var.common_tags
}

resource "aws_iam_role" "worker" {
  name               = "${var.name_prefix}-deployment-worker"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags               = var.common_tags
}

resource "aws_iam_role_policy" "worker" {
  role = aws_iam_role.worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = ["${aws_cloudwatch_log_group.worker.arn}:*", "${aws_cloudwatch_log_group.reconcile.arn}:*"] },
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:PutItem", "dynamodb:BatchWriteItem", "dynamodb:ConditionCheckItem"], Resource = var.control_table_arn },
      { Effect = "Allow", Action = ["cloudformation:CreateChangeSet", "cloudformation:DescribeChangeSet", "cloudformation:ExecuteChangeSet", "cloudformation:DeleteChangeSet", "cloudformation:DescribeStacks", "cloudformation:ListStackResources", "cloudformation:DeleteStack", "cloudformation:TagResource", "cloudformation:UntagResource"], Resource = ["${local.prefix}:cloudformation:${local.region}:${local.account}:stack/cloudhub-env-*/*", "${local.prefix}:cloudformation:${local.region}:${local.account}:changeSet/op-*/*"] },
      { Effect = "Allow", Action = "iam:PassRole", Resource = var.cfn_role_arn, Condition = { StringEquals = { "iam:PassedToService" = "cloudformation.amazonaws.com" } } },
      { Effect = "Allow", Action = ["ssm:DescribeInstanceInformation", "elasticloadbalancing:DescribeTargetHealth"], Resource = "*" },
      { Effect = "Allow", Action = ["ec2:DescribeInstances", "autoscaling:DescribeAutoScalingGroups", "ecs:ListTasks", "ecs:DescribeTasks", "elasticfilesystem:DescribeMountTargets"], Resource = "*", Condition = { StringEquals = { "aws:RequestedRegion" = local.region } } },
      { Effect = "Allow", Action = "ssm:SendCommand", Resource = "${local.prefix}:ssm:${local.region}::document/AWS-RunShellScript" },
      { Effect = "Allow", Action = "ssm:SendCommand", Resource = "${local.prefix}:ec2:${local.region}:${local.account}:instance/*", Condition = { StringEquals = { "ssm:resourceTag/Project" = "CloudHub" } } },
      { Effect = "Allow", Action = "ssm:GetCommandInvocation", Resource = "*" },
      { Effect = "Allow", Action = ["rds:DescribeDBInstances", "rds:ModifyDBInstance"], Resource = "${local.prefix}:rds:${local.region}:${local.account}:db:cloudhub-env-*" },
      { Effect = "Allow", Action = ["secretsmanager:CreateSecret", "secretsmanager:TagResource"], Resource = "${local.prefix}:secretsmanager:${local.region}:${local.account}:secret:rds!*" },
      { Effect = "Allow", Action = "kms:DescribeKey", Resource = "${local.prefix}:kms:${local.region}:${local.account}:key/*" },
      { Effect = "Allow", Action = "states:DescribeExecution", Resource = "${local.prefix}:states:${local.region}:${local.account}:execution:${var.name_prefix}-deployment:*" },
      { Effect = "Allow", Action = "sqs:SendMessage", Resource = aws_sqs_queue.failures.arn }
    ]
  })
}

resource "aws_lambda_function" "worker" {
  function_name                  = "${var.name_prefix}-deployment-worker"
  role                           = aws_iam_role.worker.arn
  runtime                        = "python3.12"
  handler                        = "cloudhub.worker.handler"
  s3_bucket                      = var.artifact_bucket
  s3_key                         = var.worker_s3_key
  timeout                        = 60
  memory_size                    = 256
  reserved_concurrent_executions = 5
  environment { variables = local.worker_env }
  tags       = var.common_tags
  depends_on = [aws_iam_role_policy.worker, aws_cloudwatch_log_group.worker]
}

resource "aws_iam_role" "workflow" {
  name = "${var.name_prefix}-deployment-workflow"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow", Principal = { Service = "states.amazonaws.com" }, Action = "sts:AssumeRole"
      Condition = { StringEquals = { "aws:SourceAccount" = local.account }, ArnEquals = { "aws:SourceArn" = local.workflow_arn } }
    }]
  })
  tags = var.common_tags
}

resource "aws_iam_role_policy" "workflow" {
  role = aws_iam_role.workflow.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "lambda:InvokeFunction", Resource = aws_lambda_function.worker.arn },
      # CloudWatch Logs delivery actions do not support log-group resource scope.
      { Effect = "Allow", Action = ["logs:CreateLogDelivery", "logs:GetLogDelivery", "logs:UpdateLogDelivery", "logs:DeleteLogDelivery", "logs:ListLogDeliveries", "logs:PutResourcePolicy", "logs:DescribeResourcePolicies", "logs:DescribeLogGroups"], Resource = "*" }
    ]
  })
}

resource "aws_sfn_state_machine" "deployment" {
  name       = "${var.name_prefix}-deployment"
  role_arn   = aws_iam_role.workflow.arn
  type       = "STANDARD"
  definition = templatefile("${path.module}/../../../workflow/deploy.asl.json", { WorkerArn = aws_lambda_function.worker.arn })
  logging_configuration {
    level                  = "ERROR"
    include_execution_data = false
    log_destination        = "${aws_cloudwatch_log_group.workflow.arn}:*"
  }
  tags       = var.common_tags
  depends_on = [aws_iam_role_policy.workflow]
}

resource "aws_sqs_queue" "failures" {
  name                      = "${var.name_prefix}-deployment-failures"
  sqs_managed_sse_enabled   = true
  message_retention_seconds = 1209600
  tags                      = var.common_tags
}

resource "aws_lambda_function" "reconcile" {
  function_name = "${var.name_prefix}-deployment-reconcile"
  role          = aws_iam_role.worker.arn
  runtime       = "python3.12"
  handler       = "cloudhub.worker.reconcile_handler"
  s3_bucket     = var.artifact_bucket
  s3_key        = var.worker_s3_key
  timeout       = 60
  memory_size   = 256
  environment { variables = merge(local.worker_env, { STATE_MACHINE_ARN = aws_sfn_state_machine.deployment.arn }) }
  dead_letter_config { target_arn = aws_sqs_queue.failures.arn }
  tags       = var.common_tags
  depends_on = [aws_iam_role_policy.worker, aws_cloudwatch_log_group.reconcile]
}

resource "aws_cloudwatch_event_rule" "interrupted" {
  name          = "${var.name_prefix}-deployment-interrupted"
  event_pattern = jsonencode({ source = ["aws.states"], "detail-type" = ["Step Functions Execution Status Change"], detail = { stateMachineArn = [aws_sfn_state_machine.deployment.arn], status = ["FAILED", "TIMED_OUT", "ABORTED"] } })
  tags          = var.common_tags
}
resource "aws_cloudwatch_event_target" "reconcile" {
  rule = aws_cloudwatch_event_rule.interrupted.name
  arn  = aws_lambda_function.reconcile.arn
  dead_letter_config { arn = aws_sqs_queue.failures.arn }
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 2
  }
}
resource "aws_lambda_permission" "eventbridge" {
  statement_id   = "ExecutionFailureEvent"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.reconcile.function_name
  principal      = "events.amazonaws.com"
  source_arn     = aws_cloudwatch_event_rule.interrupted.arn
  source_account = local.account
}
resource "aws_sqs_queue_policy" "events" {
  queue_url = aws_sqs_queue.failures.id
  policy    = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "events.amazonaws.com" }, Action = "sqs:SendMessage", Resource = aws_sqs_queue.failures.arn, Condition = { ArnEquals = { "aws:SourceArn" = aws_cloudwatch_event_rule.interrupted.arn }, StringEquals = { "aws:SourceAccount" = local.account } } }] })
}
resource "aws_cloudwatch_metric_alarm" "failed" {
  alarm_name          = "${var.name_prefix}-deployment-failed"
  namespace           = "AWS/States"
  metric_name         = "ExecutionsFailed"
  dimensions          = { StateMachineArn = aws_sfn_state_machine.deployment.arn }
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  tags                = var.common_tags
}

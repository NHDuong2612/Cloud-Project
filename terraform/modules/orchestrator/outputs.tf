output "state_machine_arn" { value = aws_sfn_state_machine.deployment.arn }
output "worker_arn" { value = aws_lambda_function.worker.arn }
output "failures_queue_arn" { value = aws_sqs_queue.failures.arn }
output "start_execution_policy" {
  value = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = "states:StartExecution", Resource = aws_sfn_state_machine.deployment.arn }] })
}

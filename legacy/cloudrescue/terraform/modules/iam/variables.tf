variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "common_tags" {
  type = map(string)
}

variable "vpc_id" {
  description = "VPC ID for security groups (from network module)"
  type        = string
  default     = null
}

variable "backup_bucket_arn" {
  description = "S3 backup bucket ARN for controller IAM policy (Task 9)"
  type        = string
  default     = null
}

variable "enable_iam" {
  description = "When true, create security groups (Task 6) and controller role/profile (Task 9)"
  type        = bool
  default     = false
}

variable "ssh_ingress_cidr" {
  description = "Optional operator CIDR for SSH to controller (e.g. x.x.x.x/32). Empty = no SSH from Internet."
  type        = string
  default     = ""
}

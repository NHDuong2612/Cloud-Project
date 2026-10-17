variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "common_tags" {
  type = map(string)
}

variable "aws_region" {
  type = string
}

variable "enable_storage" {
  description = "When true, create private S3 backup bucket"
  type        = bool
  default     = false
}

variable "noncurrent_version_expiration_days" {
  description = "Expire noncurrent object versions under backups/ after N days (cost control)"
  type        = number
  default     = 30
}

variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "common_tags" {
  type = map(string)
}

variable "private_subnet_ids" {
  type    = list(string)
  default = []
}

variable "db_security_group_id" {
  type    = string
  default = null
}

variable "db_name" {
  type = string
}

variable "db_username" {
  type = string
}

variable "db_password" {
  description = "Unused when manage_master_user_password=true; kept for API compatibility"
  type        = string
  sensitive   = true
  default     = null
}

variable "db_instance_class" {
  type = string
}

variable "db_engine_version" {
  description = "PostgreSQL major/minor; empty = AWS default for engine"
  type        = string
  default     = "16"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_availability_zone" {
  description = "Optional Single-AZ pin (e.g. ap-southeast-1a). Null = AWS chooses in subnet group."
  type        = string
  default     = null
}

variable "backup_retention_period" {
  description = "Days of automated backups (1 is enough for demo)"
  type        = number
  default     = 1
}

variable "enable_database" {
  description = "When true, create RDS (COSTS MONEY while running)"
  type        = bool
  default     = false
}

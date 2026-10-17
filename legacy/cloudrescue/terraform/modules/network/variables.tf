variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "common_tags" {
  type = map(string)
}

variable "vpc_cidr" {
  type = string
}

variable "public_subnet_cidr" {
  type = string
}

variable "private_db_subnet_cidrs" {
  type = list(string)

  validation {
    condition     = length(var.private_db_subnet_cidrs) == 2
    error_message = "private_db_subnet_cidrs must contain exactly 2 CIDRs (one per AZ)."
  }
}

variable "availability_zones" {
  description = "Optional explicit AZs (need >= 2). Empty = auto-pick first 2 in region."
  type        = list(string)
  default     = []
}

variable "enable_network" {
  description = "When true, create VPC networking resources"
  type        = bool
  default     = false
}

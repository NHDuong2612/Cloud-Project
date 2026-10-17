variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "common_tags" {
  type = map(string)
}

variable "public_subnet_id" {
  type    = string
  default = null
}

variable "controller_security_group_id" {
  type    = string
  default = null
}

variable "instance_profile_name" {
  type    = string
  default = null
}

variable "instance_type" {
  type = string
}

variable "enable_controller" {
  description = "When true, create controller EC2 (COSTS MONEY while running)"
  type        = bool
  default     = false
}

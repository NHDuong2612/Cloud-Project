variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "common_tags" {
  type = map(string)
}

variable "enable_network" {
  type    = bool
  default = false
}

variable "vpc_cidr" {
  type = string
}

variable "public_subnet_cidrs" {
  type = list(string)

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Provide exactly two public subnet CIDRs, one per AZ."
  }
}

variable "private_db_subnet_cidrs" {
  type = list(string)

  validation {
    condition     = length(var.private_db_subnet_cidrs) == 2
    error_message = "Provide exactly two private DB subnet CIDRs, one per AZ."
  }
}

variable "availability_zones" {
  type    = list(string)
  default = []

  validation {
    condition     = length(var.availability_zones) == 0 || length(var.availability_zones) == 2
    error_message = "Provide two availability zones or leave the list empty."
  }
}

variable "aws_region" {
  description = "AWS region used by CloudHub."
  type        = string
}

variable "aws_account_id" {
  description = "Expected AWS account; prevents deployment into the wrong account."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain twelve digits."
  }
}

variable "enable_platform" {
  description = "Create the TV3 control table, deployment bucket and bounded execution roles."
  type        = bool
  default     = false
}

variable "project_name" {
  description = "Resource name prefix for CloudHub."
  type        = string
  default     = "cloudhub"
}

variable "environment" {
  description = "Deployment environment such as dev."
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Owner tag identifying the team."
  type        = string
}

variable "enable_network" {
  description = "Create the shared VPC and subnets."
  type        = bool
  default     = false
}

variable "enable_storage" {
  description = "Create the private S3 recovery-artifact bucket."
  type        = bool
  default     = false
}

variable "vpc_cidr" {
  type    = string
  default = "10.30.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Two public subnet CIDRs in different AZs for load balancers and demo EC2."
  type        = list(string)
  default     = ["10.30.1.0/24", "10.30.2.0/24"]
}

variable "private_db_subnet_cidrs" {
  description = "Two private DB subnet CIDRs in different AZs."
  type        = list(string)
  default     = ["10.30.11.0/24", "10.30.12.0/24"]
}

variable "availability_zones" {
  description = "Optional two AZ names; empty selects two available AZs."
  type        = list(string)
  default     = []
}

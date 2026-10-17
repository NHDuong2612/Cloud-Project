variable "name_prefix" {
  type = string
}

variable "common_tags" {
  type = map(string)
}

variable "recovery_bucket_arn" {
  type    = string
  default = null
}

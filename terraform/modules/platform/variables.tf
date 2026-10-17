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

variable "allowed_hosted_zone_ids" {
  type    = list(string)
  default = []
}
variable "allowed_base_domain" {
  type    = string
  default = ""
}

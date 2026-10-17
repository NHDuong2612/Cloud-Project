variable "name_prefix" { type = string }
variable "common_tags" { type = map(string) }
variable "control_table_name" { type = string }
variable "control_table_arn" { type = string }
variable "artifact_bucket" { type = string }
variable "worker_s3_key" { type = string }
variable "cfn_role_arn" { type = string }
variable "platform_parameters" { type = map(string) }
variable "approved_images" {
  type    = map(string)
  default = {}
}
variable "verified_templates" {
  type    = list(string)
  default = []
}

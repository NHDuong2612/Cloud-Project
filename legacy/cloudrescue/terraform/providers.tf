# AWS provider — credentials come from CLI profile / env / SSO.
# DO NOT put access_key / secret_key in this file.
provider "aws" {
  region = var.aws_region

  # Prefer: aws configure --profile cloudrescue-dev
  # or:     aws configure sso
  # Then:   export AWS_PROFILE=cloudrescue-dev
  #
  # Optional explicit profile (uncomment if you do not use AWS_PROFILE):
  # profile = var.aws_profile

  default_tags {
    tags = local.common_tags
  }
}

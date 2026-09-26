# Provider versions — pin to avoid surprise breaking upgrades mid-project.
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Optional remote state (Phase later / Người 3). Keep commented for local demo.
  # backend "s3" {
  #   bucket = "<YOUR_TF_STATE_BUCKET>"
  #   key    = "cloudrescue/dev/terraform.tfstate"
  #   region = "<YOUR_REGION>"
  # }
}

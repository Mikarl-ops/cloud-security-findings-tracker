terraform {
  required_version = "= 1.17.1"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.71.0"
    }
  }
}

provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]
  default_tags {
    tags = {
      Project     = "cloud-security-findings-tracker"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Data        = "synthetic-only"
    }
  }
}

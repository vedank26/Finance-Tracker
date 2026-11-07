terraform {
  # Terraform 1.11+ is required for ephemeral values (ephemeral = true on variables)
  required_version = ">= 1.11.0"

  required_providers {
    # AWS Provider 5.88+ is required for write-only arguments (password_wo and value_wo)
    # Pin to "~> 5.88" (>= 5.88.0, < 6.0.0) to prevent breaking changes from major version upgrades
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.88"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      Component   = "Application-Infrastructure"
      ManagedBy   = "Terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

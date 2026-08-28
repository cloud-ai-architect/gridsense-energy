###############################################################################
# DataCurator - Root Terraform Configuration
# -----------------------------------------------------------------------------
# Provisions the full DataCurator stack: S3 buckets, DynamoDB, Lambdas, Step
# Function, API Gateway, CloudFront, IAM, and Resource Group.
###############################################################################

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Backend is configured via -backend-config flags; see scripts/bootstrap.sh
  backend "s3" {
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

provider "archive" {}
provider "random" {}

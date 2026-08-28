terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.50" }
  }
}

variable "arn" {
  description = "ARN of the GitHub OIDC provider (read-only, already exists)"
  type        = string
}

data "aws_iam_openid_connect_provider" "github" {
  arn = var.arn
}

output "provider_arn" {
  description = "ARN of the GitHub OIDC provider"
  value       = data.aws_iam_openid_connect_provider.github.arn
}

output "thumbprint_list" {
  description = "Thumbprint list of the GitHub OIDC provider"
  value       = data.aws_iam_openid_connect_provider.github.thumbprint_list
}

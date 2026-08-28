terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.50" }
  }
}

variable "oidc_url" { type = string }
variable "client_id" { type = string }
variable "thumbprint" { type = string }
variable "common_tags" {
  type    = map(string)
  default = {}
}

data "aws_iam_openid_connect_provider" "github" {
  url             = var.oidc_url
  client_id_list  = [var.client_id]
  thumbprint_list = [var.thumbprint]
  tags            = var.common_tags
}

output "provider_arn" { value = data.aws_iam_openid_connect_provider.github.arn }

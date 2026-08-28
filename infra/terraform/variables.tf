###############################################################################
# Input variables. All account-specific values come from envs/<env>.tfvars.
###############################################################################

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name; used as prefix for all resources"
  type        = string
  default     = "gridsense"
}

variable "owner" {
  description = "Resource owner (tag value)"
  type        = string
  default     = "vijay"
}

variable "cost_center" {
  description = "Cost center tag (for billing allocation)"
  type        = string
  default     = "portfolio"
}

variable "github_org" {
  description = "GitHub organization or user that owns this repo"
  type        = string
  default     = "cloud-ai-architect"
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "gridsense-energy"
}

variable "bedrock_model_id" {
  description = "Bedrock model for agents"
  type        = string
  default     = "anthropic.claude-sonnet-4-5-20250929-v1:0"
}

variable "bedrock_haiku_model_id" {
  description = "Bedrock model for orchestrator (cheap)"
  type        = string
  default     = "anthropic.claude-haiku-4-5-20250929-v1:0"
}

variable "embedding_dimensions" {
  description = "Embedding dimensions; must match the model"
  type        = number
  default     = 1024
}

variable "lambda_runtime" {
  description = "Lambda Python runtime"
  type        = string
  default     = "python3.12"
}

variable "lambda_memory_mb" {
  description = "Lambda memory (MB)"
  type        = number
  default     = 512
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout (seconds)"
  type        = number
  default     = 300
}

variable "enable_cloudfront" {
  description = "Create CloudFront distribution in front of UI bucket"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "monthly_budget_usd" {
  description = "Monthly budget for cost alarms (USD)"
  type        = number
  default     = 50
}

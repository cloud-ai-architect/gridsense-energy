terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.50" }
  }
}

variable "name_prefix" { type = string }
variable "state_machine_arn" { type = string }
variable "lambda_arns" { type = map(string) }
variable "common_tags" {
  type = map(string)
  default = {}
}

locals {
  asl_definition = jsonencode({
    Comment = "RetailPulse conversation pipeline"
    StartAt = "Orchestrator"
    States = {
      Orchestrator = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          "FunctionName" = var.lambda_arns["orchestrator"]
          "Payload.$"    = "$"
        }
        Retry = [{
          ErrorEquals    = ["States.TaskFailed"]
          IntervalSeconds = 1
          MaxAttempts    = 3
          BackoffRate    = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next       = "Failed"
        }]
        Next = "Dispatch"
      }
      Dispatch = {
        Type = "Choice"
        Choices = [
          { Variable = "$.intent", StringEquals = "sales",   Next = "SalesAgent" },
          { Variable = "$.intent", StringEquals = "support", Next = "SupportAgent" },
          { Variable = "$.intent", StringEquals = "returns", Next = "ReturnsAgent" }
        ]
        Default = "Failed"
      }
      SalesAgent = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          "FunctionName" = var.lambda_arns["sales"]
          "Payload.$"    = "$"
        }
        Retry = [{
          ErrorEquals    = ["States.TaskFailed"]
          IntervalSeconds = 1
          MaxAttempts    = 3
          BackoffRate    = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next       = "Failed"
        }]
        End = true
      }
      SupportAgent = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          "FunctionName" = var.lambda_arns["support"]
          "Payload.$"    = "$"
        }
        Retry = [{
          ErrorEquals    = ["States.TaskFailed"]
          IntervalSeconds = 1
          MaxAttempts    = 3
          BackoffRate    = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next       = "Failed"
        }]
        End = true
      }
      ReturnsAgent = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          "FunctionName" = var.lambda_arns["returns"]
          "Payload.$"    = "$"
        }
        Retry = [{
          ErrorEquals    = ["States.TaskFailed"]
          IntervalSeconds = 1
          MaxAttempts    = 3
          BackoffRate    = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next       = "Failed"
        }]
        End = true
      }
      Failed = { Type = "Fail", Cause = "Pipeline failed" }
    }
  })
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/vendedlogs/states/${var.name_prefix}-pipeline"
  retention_in_days = 30
  tags              = var.common_tags
}

resource "aws_sfn_state_machine" "this" {
  name     = "${var.name_prefix}-pipeline"
  role_arn = var.state_machine_arn

  definition = local.asl_definition

  tracing_configuration {
    enabled = true
  }

  tags = var.common_tags
}

output "state_machine_arn" { value = aws_sfn_state_machine.this.arn }
output "state_machine_name" { value = aws_sfn_state_machine.this.name }

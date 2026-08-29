###############################################################################
# Pipeline state machine.
#
# Orchestrator classifies the request, then a Choice state dispatches to the
# stage that handles it. Each task unwraps the lambda:invoke envelope with
# OutputPath so the next state receives the payload rather than the
# {Payload, StatusCode, ExecutedVersion} wrapper.
###############################################################################

terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.50" }
  }
}

variable "name_prefix" { type = string }
variable "lambda_arns" { type = map(string) }
variable "state_machine_arn" { type = string }
variable "common_tags" {
  type    = map(string)
  default = {}
}

locals {
  definition = {
    Comment = "${var.name_prefix} pipeline"
    StartAt = "Orchestrator"
    States = {
      Orchestrator = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"

        Parameters = {
          "FunctionName" = var.lambda_arns["orchestrator"]
          "Payload.$"    = "$"
        }

        OutputPath = "$.Payload"

        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 1
          MaxAttempts     = 3
          BackoffRate     = 2.0
        }]

        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "Failed"
        }]

        Next = "Dispatch"
      }

      Dispatch = {
        Type = "Choice"
        Choices = [
          { Variable = "$.agent", StringEquals = "forecast", Next = "ForecastStage" },
          { Variable = "$.agent", StringEquals = "anomaly", Next = "AnomalyStage" },
          { Variable = "$.agent", StringEquals = "dispatch", Next = "DispatchStage" },
          { Variable = "$.agent", StringEquals = "explain", Next = "ExplainStage" }
        ]
        Default = "Failed"
      }

      ForecastStage = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"

        Parameters = {
          "FunctionName" = var.lambda_arns["forecast"]
          "Payload.$"    = "$"
        }

        OutputPath = "$.Payload"

        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 1
          MaxAttempts     = 3
          BackoffRate     = 2.0
        }]

        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "Failed"
        }]

        End = true
      }

      AnomalyStage = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"

        Parameters = {
          "FunctionName" = var.lambda_arns["anomaly"]
          "Payload.$"    = "$"
        }

        OutputPath = "$.Payload"

        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 1
          MaxAttempts     = 3
          BackoffRate     = 2.0
        }]

        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "Failed"
        }]

        End = true
      }

      DispatchStage = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"

        Parameters = {
          "FunctionName" = var.lambda_arns["dispatch"]
          "Payload.$"    = "$"
        }

        OutputPath = "$.Payload"

        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 1
          MaxAttempts     = 3
          BackoffRate     = 2.0
        }]

        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "Failed"
        }]

        End = true
      }

      ExplainStage = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"

        Parameters = {
          "FunctionName" = var.lambda_arns["explain"]
          "Payload.$"    = "$"
        }

        OutputPath = "$.Payload"

        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 1
          MaxAttempts     = 3
          BackoffRate     = 2.0
        }]

        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "Failed"
        }]

        End = true
      }


      Failed = { Type = "Fail", Cause = "Pipeline failed" }
    }
  }
}

resource "aws_sfn_state_machine" "this" {
  name       = "${var.name_prefix}-pipeline"
  role_arn   = var.state_machine_arn
  definition = jsonencode(local.definition)
  tags       = var.common_tags
}

output "state_machine_arn" { value = aws_sfn_state_machine.this.arn }

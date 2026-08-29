###############################################################################
# HTTP API in front of the agent Lambdas.
#
# Previously this exposed the retail template's routes -- /v1/catalog/search
# and /v1/conversations -- both wired to the same function, and the
# orchestrator was not reachable at all.
#
# Routes are now driven by a map so each agent gets its own endpoint and
# adding an agent is a one-line change rather than four resources.
###############################################################################

terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.50" }
  }
}

variable "name_prefix" { type = string }
variable "api_description" {
  type    = string
  default = "Agent API"
}

# route path suffix => lambda invoke arn
variable "routes" {
  type = map(string)
}

variable "common_tags" {
  type    = map(string)
  default = {}
}

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.name_prefix}-api"
  protocol_type = "HTTP"
  description   = var.api_description

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization", "X-Amz-Date", "X-Amz-Security-Token"]
    max_age       = 300
  }

  tags = var.common_tags
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true
  tags        = var.common_tags
}

resource "aws_apigatewayv2_integration" "this" {
  for_each = var.routes

  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = each.value
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "this" {
  for_each = var.routes

  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /v1/${each.key}"
  target    = "integrations/${aws_apigatewayv2_integration.this[each.key].id}"
}

# Lambda permissions are per function rather than per route: several routes
# may share a function, and a duplicate statement_id would fail.
resource "aws_lambda_permission" "this" {
  for_each = var.routes

  statement_id  = "AllowAPIGatewayInvoke-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = each.value
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}

output "api_id"     { value = aws_apigatewayv2_api.this.id }
output "api_url"    { value = aws_apigatewayv2_api.this.api_endpoint }
output "stage_name" { value = aws_apigatewayv2_stage.this.name }
output "routes"     { value = [for k, _ in var.routes : "POST /v1/${k}"] }

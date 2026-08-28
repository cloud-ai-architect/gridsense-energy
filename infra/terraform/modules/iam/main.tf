###############################################################################
# IAM - all roles and policies consolidated for fast deployment
###############################################################################

terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.50" }
  }
}

# --- GitHub OIDC role (assumes the role from the OIDC trust policy) ---

data "aws_iam_policy_document" "github_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = [var.github_aud]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [var.github_sub_main, var.github_sub_pr]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "${var.name_prefix}-github-deploy-role"
  assume_role_policy = data.aws_iam_policy_document.github_trust.json
  tags               = var.common_tags
}

data "aws_iam_policy_document" "github_actions_inline" {
  statement {
    sid     = "AllActionsOnRetailPulse"
    effect  = "Allow"
    actions = ["*"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Project"
      values   = [var.project_name]
    }
  }
}

resource "aws_iam_role_policy" "github_actions" {
  name   = "${var.project_name}-deploy-permissions"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.github_actions_inline.json
}

# --- Lambda execution role (shared) ---

resource "aws_iam_role" "lambda_exec" {
  name = "${var.name_prefix}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

data "aws_iam_policy_document" "lambda_basic" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "arn:aws:logs:*:*:log-group:/aws/lambda/${var.name_prefix}-*:*",
    ]
  }
}

resource "aws_iam_role_policy" "lambda_basic" {
  name   = "basic-execution"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_basic.json
}

data "aws_iam_policy_document" "lambda_bedrock" {
  statement {
    sid    = "BedrockInvoke"
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]

    resources = [
      "arn:aws:bedrock:*:*:foundation-model/*",
    ]
  }
}

resource "aws_iam_role_policy" "lambda_bedrock" {
  name   = "bedrock-invoke"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_bedrock.json
}

data "aws_iam_policy_document" "lambda_dynamodb" {
  statement {
    sid    = "DynamoDBAccess"
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
    ]

    resources = [
      "arn:aws:dynamodb:*:*:table/${var.tables.orders}",
      "arn:aws:dynamodb:*:*:table/${var.tables.orders}/index/*",
      "arn:aws:dynamodb:*:*:table/${var.tables.feedback}",
      "arn:aws:dynamodb:*:*:table/${var.tables.feedback}/index/*",
      "arn:aws:dynamodb:*:*:table/${var.tables.coversations}",
      "arn:aws:dynamodb:*:*:table/${var.tables.coversations}/index/*",
    ]
  }
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name   = "dynamodb-access"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_dynamodb.json
}

data "aws_iam_policy_document" "lambda_s3" {
  statement {
    sid    = "CatalogReadWrite"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
    ]

    resources = [
      "arn:aws:s3:::${var.buckets.catalog}",
      "arn:aws:s3:::${var.buckets.catalog}/*",
      "arn:aws:s3:::${var.buckets.ui}",
      "arn:aws:s3:::${var.buckets.ui}/*",
    ]
  }
}

resource "aws_iam_role_policy" "lambda_s3" {
  name   = "s3-access"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_s3.json
}

data "aws_iam_policy_document" "lambda_voice" {
  statement {
    sid    = "VoiceServices"
    effect = "Allow"

    actions = [
      "polly:SynthesizeSpeech",
      "polly:DescribeVoices",
      "transcribe:StartTranscriptionJob",
      "transcribe:GetTranscriptionJob",
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_voice" {
  name   = "voice-access"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_voice.json
}

# --- Step Function role ---

resource "aws_iam_role" "step_function" {
  name = "${var.name_prefix}-step-function-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

data "aws_iam_policy_document" "step_function" {
  statement {
    sid     = "InvokeLambdas"
    effect  = "Allow"
    actions = ["lambda:InvokeFunction"]

    resources = [
      "arn:aws:lambda:*:*:function:${var.name_prefix}-*",
    ]
  }
}

resource "aws_iam_role_policy" "step_function" {
  name   = "step-function"
  role   = aws_iam_role.step_function.id
  policy = data.aws_iam_policy_document.step_function.json
}

# --- Vectors role (for S3 Vectors access) ---

resource "aws_iam_role" "vectors" {
  name = "${var.name_prefix}-vectors-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = aws_iam_role.lambda_exec.arn }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

data "aws_iam_policy_document" "vectors_inline" {
  statement {
    sid    = "VectorsAccess"
    effect = "Allow"

    actions = [
      "s3vectors:GetVectors",
      "s3vectors:PutVectors",
      "s3vectors:DeleteVectors",
      "s3vectors:ListVectors",
      "s3vectors:QueryVectors",
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "vectors" {
  name   = "vectors-access"
  role   = aws_iam_role.vectors.id
  policy = data.aws_iam_policy_document.vectors_inline.json
}

resource "aws_iam_role_policy" "lambda_assume_vectors" {
  name = "assume-vectors-role"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "sts:AssumeRole"
      Resource = aws_iam_role.vectors.arn
    }]
  })
}

# --- API Gateway invoke role ---

resource "aws_iam_role" "apigateway" {
  name = "${var.name_prefix}-apigateway-invoke-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "apigateway.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

# --- EventBridge role ---

resource "aws_iam_role" "eventbridge" {
  name = "${var.name_prefix}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

data "aws_iam_policy_document" "eventbridge" {
  statement {
    sid     = "StartStepFunction"
    effect  = "Allow"
    actions = ["states:StartExecution"]

    resources = [
      "arn:aws:states:*:*:stateMachine:${var.name_prefix}-*",
    ]
  }
}

resource "aws_iam_role_policy" "eventbridge" {
  name   = "eventbridge"
  role   = aws_iam_role.eventbridge.id
  policy = data.aws_iam_policy_document.eventbridge.json
}

# --- Outputs ---

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda_exec.arn
}

output "lambda_role_arns" {
  value = { for k, v in var.lambdas : k => aws_iam_role.lambda_exec.arn }
}

output "api_role_arn" {
  value = aws_iam_role.lambda_exec.arn
}

output "api_role_arns" {
  value = { for k, v in var.lambdas : k => aws_iam_role.lambda_exec.arn }
}

output "vectors_role_arn" {
  value = aws_iam_role.vectors.arn
}

output "step_function_role_arn" {
  value = aws_iam_role.step_function.arn
}

output "eventbridge_role_arn" {
  value = aws_iam_role.eventbridge.arn
}

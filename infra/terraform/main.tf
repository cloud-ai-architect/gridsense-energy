###############################################################################
# DataCurator - Main Terraform
###############################################################################

locals {
  buckets = {
    catalog = "${local.name_prefix}-catalog"
    vectors = "${local.name_prefix}-vectors"
    ui      = "${local.name_prefix}-ui"
  }

  tables = {
    orders      = "${local.name_prefix}-orders"
    feedback    = "${local.name_prefix}-feedback"
    coversations = "${local.name_prefix}-conversations"
  }

  lambdas = {
    orchestrator = "${local.name_prefix}-orchestrator"
    sales        = "${local.name_prefix}-sales"
    support      = "${local.name_prefix}-support"
    returns      = "${local.name_prefix}-returns"
    search       = "${local.name_prefix}-search"
    feedback     = "${local.name_prefix}-feedback"
  }

  github_oidc_arn = "arn:aws:iam::761554981898:oidc-provider/token.actions.githubusercontent.com"
}

# --- OIDC + IAM ---

module "oidc" {
  source = "./modules/oidc"
  arn    = local.github_oidc_arn
}

module "iam" {
  source = "./modules/iam"

  project_name      = var.project_name
  environment       = var.environment
  name_prefix       = local.name_prefix
  github_org        = var.github_org
  github_repo       = var.github_repo
  github_sub_main   = local.github_sub_main
  github_sub_pr     = local.github_sub_pr
  github_aud        = local.github_aud
  github_thumbprint = local.github_thumbprint
  buckets           = local.buckets
  tables            = local.tables
  lambdas           = local.lambdas
  vector_index_name = local.vector_index_name
  oidc_provider_arn = module.oidc.provider_arn
  common_tags       = local.common_tags
}

# --- Storage ---

module "catalog_bucket" {
  source = "./modules/s3-bucket"

  bucket_name  = local.buckets.catalog
  common_tags  = local.common_tags
  allow_public = false
}

module "vectors_bucket" {
  source = "./modules/s3-vectors-bucket"

  bucket_name      = local.buckets.vectors
  index_name       = local.vector_index_name
  embedding_dim    = var.embedding_dimensions
  common_tags      = local.common_tags
  vectors_role_arn = module.iam.vectors_role_arn
}

module "ui_bucket" {
  source = "./modules/s3-bucket"

  bucket_name  = local.buckets.ui
  common_tags  = local.common_tags
  allow_public = true
}

module "orders_dynamodb" {
  source = "./modules/dynamodb-orders"

  table_name  = local.tables.orders
  common_tags = local.common_tags
}

module "feedback_dynamodb" {
  source = "./modules/dynamodb-feedback"

  table_name  = local.tables.feedback
  common_tags = local.common_tags
}

module "conversations_dynamodb" {
  source = "./modules/dynamodb-conversations"

  table_name  = local.tables.coversations
  common_tags = local.common_tags
}

# --- Compute ---

module "lambdas" {
  source = "./modules/lambdas"

  project_name        = var.project_name
  environment         = var.environment
  name_prefix         = local.name_prefix
  lambdas             = local.lambdas
  lambda_runtime      = var.lambda_runtime
  lambda_memory_mb    = var.lambda_memory_mb
  lambda_timeout      = var.lambda_timeout_seconds
  buckets             = local.buckets
  tables              = local.tables
  vector_index_name   = local.vector_index_name
  bedrock_model_id    = var.bedrock_model_id
  haiku_model_id      = var.bedrock_haiku_model_id
  lambda_role_arns    = module.iam.lambda_role_arns
  api_role_arns       = module.iam.api_role_arns
  log_retention_days  = var.log_retention_days
  common_tags         = local.common_tags
}

module "step_function" {
  source = "./modules/step-function"

  name_prefix       = local.name_prefix
  state_machine_arn = module.iam.step_function_role_arn
  lambda_arns       = module.lambdas.function_arns
  common_tags       = local.common_tags
}

module "eventbridge" {
  source = "./modules/eventbridge"

  name_prefix       = local.name_prefix
  bucket_name       = local.buckets.catalog
  state_machine_arn = module.step_function.state_machine_arn
  common_tags       = local.common_tags
}

# --- API + UI ---

module "apigateway" {
  source = "./modules/apigateway"

  name_prefix     = local.name_prefix
  search_lambda   = module.lambdas.function_arns["search"]
  feedback_lambda = module.lambdas.function_arns["feedback"]
  common_tags     = local.common_tags
}

module "cloudfront" {
  source = "./modules/cloudfront"

  name_prefix = local.name_prefix
  ui_bucket   = local.buckets.ui
  api_url     = module.apigateway.api_url
  enabled     = var.enable_cloudfront
  common_tags = local.common_tags
}

# --- Resource Group ---

module "resource_group" {
  source = "./modules/resource-group"

  name_prefix = local.name_prefix
  environment = var.environment
  common_tags = local.common_tags
}

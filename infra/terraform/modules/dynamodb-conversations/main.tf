terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.50" }
  }
}

variable "table_name" { type = string }
variable "common_tags" {
  type    = map(string)
  default = {}
}

resource "aws_dynamodb_table" "this" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  tags         = var.common_tags

  attribute {
    name = "session_id"
    type = "S"
  }
  attribute {
    name = "customer_id"
    type = "S"
  }
  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "customer-index"
    hash_key        = "customer_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery { enabled = true }
  server_side_encryption { enabled = true }
}

output "table_arn" { value = aws_dynamodb_table.this.arn }

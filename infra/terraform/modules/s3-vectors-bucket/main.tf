terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws    = { source = "hashicorp/aws",    version = "~> 5.50" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

variable "bucket_name" { type = string }
variable "index_name" { type = string }
variable "embedding_dim" {
  type = number
  default = 1024
}
variable "common_tags" {
  type = map(string)
  default = {}
}
variable "vectors_role_arn" { type = string }

resource "aws_kms_key" "this" {
  description             = "KMS key for ${var.bucket_name}"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = var.common_tags
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.bucket_name}"
  target_key_id = aws_kms_key.this.key_id
}

resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  tags   = var.common_tags
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.this.arn
    }
    bucket_key_enabled = true
  }
}

# S3 Vectors (no native resource — use null_resource workaround)
resource "random_id" "this" {
  byte_length = 4
  keepers = {
    bucket = var.bucket_name
    index  = var.index_name
  }
}

resource "null_resource" "s3_vector_bucket" {
  triggers = {
    bucket_name = var.bucket_name
    index_name  = var.index_name
  }

  provisioner "local-exec" {
    command = <<EOF
aws s3vectors create-vector-bucket --vector-bucket-name "${var.bucket_name}" --region ap-south-1 || echo "Bucket may already exist"
aws s3vectors create-index --vector-bucket-name "${var.bucket_name}" --index-name "${var.index_name}" --dimension ${var.embedding_dim} --distance-metric cosine --region ap-south-1 || echo "Index may already exist"
EOF
  }
}

output "bucket_arn"    { value = aws_s3_bucket.this.arn }
output "bucket_name"   { value = aws_s3_bucket.this.bucket }
output "vector_bucket" { value = var.bucket_name }
output "index_arn"     { value = "arn:aws:s3vectors:ap-south-1:${data.aws_caller_identity.current.account_id}:vector-bucket/${var.bucket_name}/index/${var.index_name}" }
output "index_name"    { value = var.index_name }
output "kms_key_arn"   { value = aws_kms_key.this.arn }

data "aws_caller_identity" "current" {}

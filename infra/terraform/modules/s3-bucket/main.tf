terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.50" }
  }
}

variable "bucket_name" { type = string }
variable "common_tags" {
  type    = map(string)
  default = {}
}
variable "allow_public" {
  type    = bool
  default = false
}

resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  tags   = var.common_tags
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = !var.allow_public
  block_public_policy     = !var.allow_public
  ignore_public_acls      = !var.allow_public
  restrict_public_buckets = !var.allow_public
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    id = "expire-old-ingests"
    filter { prefix = "" }
    status = "Enabled"
    expiration { days = 30 }
    noncurrent_version_expiration { noncurrent_days = 7 }
  }
}

output "bucket_arn" { value = aws_s3_bucket.this.arn }
output "bucket_name" { value = aws_s3_bucket.this.bucket }
output "bucket_domain" { value = aws_s3_bucket.this.bucket_domain_name }

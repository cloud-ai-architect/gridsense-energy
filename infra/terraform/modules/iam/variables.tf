variable "project_name" { type = string }
variable "environment" { type = string }
variable "name_prefix" { type = string }
variable "github_org" { type = string }
variable "github_repo" { type = string }
variable "github_sub_main" { type = string }
variable "github_sub_pr" { type = string }
variable "github_aud" { type = string }
variable "github_thumbprint" { type = string }
variable "buckets" { type = map(string) }
variable "tables" { type = map(string) }
variable "lambdas" { type = map(string) }
variable "vector_index_name" { type = string }
variable "oidc_provider_arn" { type = string }
variable "common_tags" {
  type    = map(string)
  default = {}
}

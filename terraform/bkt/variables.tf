variable "bucket_name" {
  description = "Nome do bucket S3 onde o Terraform armazenará o state"
  type        = string
}

variable "region" {
  description = "Região AWS"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Nome do ambiente (ex: dev, staging, prod)"
  type        = string
  default     = "dev"
}

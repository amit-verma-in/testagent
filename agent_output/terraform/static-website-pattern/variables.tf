variable "aws_region" {
  description = "The AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "The name of the S3 bucket for hosting the static website"
  type        = string
}

variable "kms_key_arn" {
  description = "The AWS KMS master key ARN used for S3 SSE-KMS encryption"
  type        = string
}

variable "product_id" {
  description = "Product ID for resource tagging and tracking"
  type        = string
}

variable "environment" {
  description = "Environment type (e.g., prod, non_prod, sbx)"
  type        = string
  default     = "prod"
}

variable "certificate_arn" {
  description = "The ARN of the ACM certificate to use for the CloudFront distribution"
  type        = string
}

variable "log_bucket_domain_name" {
  description = "The domain name of the S3 bucket used for CloudFront access logs"
  type        = string
}

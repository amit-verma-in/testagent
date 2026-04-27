variable "aws_region" {
  type        = string
  description = "The AWS region to deploy to"
  default     = "us-east-1"
}

variable "bucket_name" {
  type        = string
  description = "The name of the S3 bucket to host the static website"
}

variable "kms_key_arn" {
  type        = string
  description = "The ARN of the KMS key used to encrypt the S3 bucket"
}

variable "cloudfront_name" {
  type        = string
  description = "The name of the CloudFront distribution"
}

variable "product_id" {
  type        = string
  description = "Product ID for the CloudFront distribution tagging"
}

variable "environment" {
  type        = string
  description = "Deployment environment (e.g., non_prod, prod, sbx)"
  default     = "non_prod"
}

provider "aws" {
  region = var.aws_region
}

module "s3_website" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/s3/aws"
  version = "3.0.2"

  name        = var.bucket_name
  kms_key_arn = var.kms_key_arn

  # Static Website Configuration
  static_website_config_enabled = true
  index_document                = "index.html"
  error_document                = "error.html"

  # Security (No public bucket, use CloudFront OAC)
  object_ownership            = "BucketOwnerEnforced"
  cloudfront_distribution_arn = module.cloudfront.cloudfront_distribution_arn
}

module "cloudfront" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/cloudfront/aws"
  version = "0.2.1"

  name       = var.cloudfront_name
  product_id = var.product_id
  used_for   = var.environment

  default_root_object = "index.html"

  create_origin_access_control = true

  origin = {
    s3 = {
      domain_name           = module.s3_website.bucket_regional_domain_name
      origin_access_control = "s3"
    }
  }

  default_cache_behavior = {
    target_origin_id       = "s3"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD"]
    cached_methods  = ["GET", "HEAD"]

    forwarded_values = {
      query_string = false
      cookies = {
        forward = "none"
      }
    }
  }
}

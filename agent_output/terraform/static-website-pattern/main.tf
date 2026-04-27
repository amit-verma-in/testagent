terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.58, < 7.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "s3_website" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/s3/aws"
  version = "3.0.2"

  name                          = var.bucket_name
  kms_key_arn                   = var.kms_key_arn
  static_website_config_enabled = true

  # Integrates automatically with CloudFront OAC bucket policy
  cloudfront_distribution_arn = module.cloudfront.cloudfront_distribution_arn
}

module "cloudfront" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/cloudfront/aws"
  version = "0.2.1"

  name                = "${var.bucket_name}-cf"
  product_id          = var.product_id
  used_for            = var.environment
  default_root_object = "index.html"

  create_origin_access_control = true

  origin = {
    s3_origin = {
      domain_name           = module.s3_website.bucket_regional_domain_name
      origin_access_control = "s3"
    }
  }

  default_cache_behavior = {
    target_origin_id       = "s3_origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
  }

  # Enforce TLS 1.2+ and use a custom certificate to align with firm security standards
  viewer_certificate = {
    cloudfront_default_certificate = false
    acm_certificate_arn            = var.certificate_arn
    minimum_protocol_version       = "TLSv1.2_2021"
    ssl_support_method             = "sni-only"
  }

  # Enable logging to satisfy Wiz security policies
  logging_config = {
    bucket = var.log_bucket_domain_name
    prefix = "cf-logs/"
  }
}

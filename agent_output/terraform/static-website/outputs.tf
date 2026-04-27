output "website_bucket_name" {
  description = "The name of the S3 bucket"
  value       = module.s3_website.name
}

output "website_bucket_arn" {
  description = "The ARN of the S3 bucket"
  value       = module.s3_website.arn
}

output "cloudfront_domain_name" {
  description = "The domain name of the CloudFront distribution"
  value       = module.cloudfront.cloudfront_distribution_domain_name
}

output "cloudfront_distribution_id" {
  description = "The ID of the CloudFront distribution"
  value       = module.cloudfront.cloudfront_distribution_id
}

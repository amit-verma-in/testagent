# Secure Static Website on AWS

This Terraform stack provisions a secure, production-ready static website on AWS using McKinsey Pattern Catalogue modules.

## Architecture

* **Amazon S3**: Hosts the static assets (HTML, CSS, JS, images). The bucket is completely private and secure with `BucketOwnerEnforced` object ownership and SSE-KMS encryption.
* **Amazon CloudFront**: Acts as the Content Delivery Network (CDN) to distribute traffic globally. It uses Origin Access Control (OAC) to securely authenticate with the private S3 bucket. All traffic is enforced over HTTPS.

## Modules Used
* `FIRM-TF-MODULES/s3/aws` (v3.0.2)
* `FIRM-TF-MODULES/cloudfront/aws` (v0.2.1)

## Inputs
* `bucket_name`: The globally unique S3 bucket name.
* `kms_key_arn`: The ARN of the KMS Key used for bucket encryption.
* `cloudfront_name`: The name for the CloudFront distribution.
* `product_id`: The billing/product ID tag required by the firm.
* `environment`: Deployment environment (e.g. `non_prod`, `prod`, `sbx`).
* `aws_region`: AWS region to deploy into (default `us-east-1`).

## Outputs
* `website_bucket_name`: The created S3 bucket to upload files to.
* `cloudfront_domain_name`: The URL (domain) through which the website can be accessed securely.

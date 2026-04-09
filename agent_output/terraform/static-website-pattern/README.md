# AWS Static Website Stack

This stack provisions a secure, production-ready static website using AWS S3 and CloudFront, leveraging the approved internal Pattern Catalogue modules (`FIRM-TF-MODULES/s3/aws` and `FIRM-TF-MODULES/cloudfront/aws`).

## Features
- **S3 Bucket**: Deploys a private S3 bucket tailored for static website hosting, utilizing `BucketOwnerEnforced` with ACLs disabled.
- **CloudFront Distribution**: Serves as the CDN for the website, accelerating content delivery.
- **Origin Access Control (OAC)**: Secures the S3 origin by ensuring it can only be accessed through the CloudFront distribution.
- **Security & Compliance**: Automatically enforces TLS 1.2 minimum protocols, disables the insecure default AWS certificate, and mandates CloudFront access logging to comply with Wiz block policies.

## Usage
Since CloudFront OAC requires the S3 bucket policy to reference the CloudFront distribution ARN, and the CloudFront distribution references the S3 bucket domain, you may encounter a **circular dependency** upon the initial deployment.

To resolve this on the very first run, you can either:
1. Use targeted applies: 
   `terraform apply -target=module.cloudfront` followed by a full `terraform apply`.
2. Temporarily comment out `cloudfront_distribution_arn` in the `s3_website` module during the first apply, and add it back for the second apply.

Provide the required inputs in your `terraform.tfvars` file:

```hcl
aws_region             = "us-east-1"
bucket_name            = "my-secure-static-site"
kms_key_arn            = "arn:aws:kms:us-east-1:123456789012:key/..."
product_id             = "PRD-12345"
environment            = "prod"
certificate_arn        = "arn:aws:acm:us-east-1:123456789012:certificate/..."
log_bucket_domain_name = "my-logging-bucket.s3.amazonaws.com"
```

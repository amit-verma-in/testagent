# SageMaker Notebook (Refactored)

This stack has been automatically refactored from a CloudFormation template to use the firm's approved **Pattern Catalogue** modules (`sagemaker` and `sagemaker-iam`). 

## Features
- Connects automatically to the approved SageMaker IAM module to enforce least-privilege constraints on S3 buckets.
- Disables direct internet access and root access for the notebook environment by default, ensuring compliance.
- Supports provisioning inside a specific VPC & subnet with a customer-managed KMS key.

## Requirements
- Supply `vpc_id` and `subnet_ids` for deployment.
- Supply `s3_buckets` array for the role permissions.

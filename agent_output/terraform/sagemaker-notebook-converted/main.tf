terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.23, < 7.0"
    }
  }
}

provider "aws" {
  # Configure your AWS region here
}

# Approved IAM Module for SageMaker
module "sagemaker_iam" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/sagemaker-iam/aws"
  version = "0.4.0"

  name       = "${var.name}-notebook-role"
  s3_buckets = var.s3_buckets
}

# Approved SageMaker Module (Notebook & Domain)
module "sagemaker_notebook" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/sagemaker/aws"
  version = "0.1.1"

  name              = var.name
  instance_type     = var.instance_type
  vpc_id            = var.vpc_id
  subnet_ids        = var.subnet_ids
  kms_key_id        = var.kms_key_id
  sagemaker_iam_arn = module.sagemaker_iam.arn

  # Firm Defaults for secure Notebook instances
  direct_internet_access = "Disabled"
  root_access            = "Disabled"
}

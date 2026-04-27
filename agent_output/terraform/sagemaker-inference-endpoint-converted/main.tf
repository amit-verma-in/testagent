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

  name       = "${var.name}-model-role"
  s3_buckets = var.s3_buckets
}

# The Pattern Catalogue does not have a dedicated Inference Endpoint module, 
# so we use native resources securely bound to the approved IAM role.

resource "aws_sagemaker_model" "this" {
  name               = "${var.name}-model"
  execution_role_arn = module.sagemaker_iam.arn

  primary_container {
    image          = var.image_url
    model_data_url = var.model_data_url
  }
}

resource "aws_sagemaker_endpoint_configuration" "this" {
  name = "${var.name}-endpoint-config"

  production_variants {
    variant_name           = "AllTraffic"
    model_name             = aws_sagemaker_model.this.name
    initial_instance_count = var.initial_instance_count
    instance_type          = var.instance_type
  }
}

resource "aws_sagemaker_endpoint" "this" {
  name                 = "${var.name}-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.this.name
}

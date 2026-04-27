terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.23, < 7.0"
    }
  }
}

provider "aws" {
  # Specify your region and other configuration options
}

module "aurora" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/rds-aurora/aws"
  version = "0.6.0"

  name           = var.cluster_name
  engine         = var.engine
  engine_version = var.engine_version

  database_name   = var.database_name
  master_username = var.master_username

  vpc_security_group_ids = var.vpc_security_group_ids
  subnets                = var.subnets

  instances = var.instances

  # Ensure storage encryption is enabled (default is true, explicitly setting for clarity)
  storage_encrypted = true

  # Automatically create a random password and output it to SSM to avoid state exposure
  output_to_ssm          = true
  create_random_password = true
}

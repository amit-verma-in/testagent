variable "name" {
  type        = string
  description = "Base name for the SageMaker resources"
  default     = "my-sagemaker-workspace"
}

variable "instance_type" {
  type        = string
  description = "Instance type for the Notebook Instance"
  default     = "ml.t2.medium"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where the Notebook will be deployed"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for the Notebook deployment"
}

variable "kms_key_id" {
  type        = string
  description = "KMS Key ID for encrypting storage volumes"
}

variable "s3_buckets" {
  type        = list(string)
  description = "List of S3 buckets the SageMaker role should have access to"
}

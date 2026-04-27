variable "name" {
  type        = string
  description = "Base name for the SageMaker Endpoint resources"
  default     = "my-inference-service"
}

variable "image_url" {
  type        = string
  description = "The ECR URI for the inference container image"
}

variable "model_data_url" {
  type        = string
  description = "The S3 URI containing the model artifacts (e.g. s3://my-bucket/model.tar.gz)"
  default     = null
}

variable "instance_type" {
  type        = string
  description = "The EC2 instance type to deploy the endpoint on"
  default     = "ml.m5.large"
}

variable "initial_instance_count" {
  type        = number
  description = "The initial number of instances to run in the endpoint"
  default     = 1
}

variable "s3_buckets" {
  type        = list(string)
  description = "List of S3 buckets the SageMaker model role needs access to (for retrieving the model artifacts)"
}

variable "aws_region" {
  type        = string
  description = "AWS region for resources."
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Name prefix for resources."
  default     = "demo-lambda-vuln"
}

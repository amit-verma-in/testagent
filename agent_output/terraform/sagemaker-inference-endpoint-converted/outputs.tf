output "sagemaker_iam_role_arn" {
  description = "The ARN of the SageMaker model execution role"
  value       = module.sagemaker_iam.arn
}

output "endpoint_name" {
  description = "The name of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.this.name
}

output "endpoint_arn" {
  description = "The ARN of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.this.arn
}

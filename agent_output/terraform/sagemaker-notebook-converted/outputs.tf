output "sagemaker_iam_role_arn" {
  description = "The ARN of the SageMaker execution role"
  value       = module.sagemaker_iam.arn
}

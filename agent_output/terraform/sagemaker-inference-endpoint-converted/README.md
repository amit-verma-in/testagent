# SageMaker Inference Endpoint (Refactored)

This stack has been automatically refactored from a CloudFormation template. While the firm Pattern Catalogue does not currently offer a dedicated module for SageMaker *Inference Endpoints* (it primarily focuses on Notebooks/Domains), we have integrated the approved `sagemaker-iam` Pattern Catalogue module to ensure the SageMaker Model Execution Role is compliant.

## Features
- Uses `sagemaker-iam` to enforce restricted bucket access for the model container.
- Connects standard Terraform `aws_sagemaker_model`, `aws_sagemaker_endpoint_configuration`, and `aws_sagemaker_endpoint` resources to build out the serving infrastructure.

## Requirements
- Provide the container `image_url` containing your inference code.
- Provide the `model_data_url` (S3 path to the model artifacts).
- Provide the `s3_buckets` array so the IAM role can retrieve the model artifacts securely.

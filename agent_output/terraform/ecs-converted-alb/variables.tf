variable "aws_region" {
  type        = string
  description = "AWS region (provider)."
  default     = "us-east-1"
}

# Generated from CloudFormation Parameters.
variable "stack_name" {
  type        = string
  description = "Stack name placeholder (maps to AWS::StackName in Sub/Ref)."
  default     = "cfn-stack"
}

variable "environment_name" {
  type        = string
  description = "Prefix for resource names."
  default     = "sample-ecs"
}

variable "vpc_id" {
  type        = string
  description = "VPC where ALB and ECS tasks run."
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "At least two public subnets in different AZs for the load balancer."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnets for ECS tasks (must have route to NAT for ECR/Docker Hub)."
}

variable "container_image" {
  type        = string
  description = "Container image URI (ECR or public)."
  default     = "public.ecr.aws/docker/library/nginx:alpine"
}

variable "container_port" {
  type        = number
  description = "Port the container listens on (must match target group)."
  default     = 80
}

variable "desired_count" {
  type        = number
  description = "Number of Fargate tasks to run."
  default     = 1
}

variable "task_cpu" {
  type        = string
  description = "Fargate task CPU units."
  default     = "256"
}

variable "task_memory" {
  type        = string
  description = "Fargate task memory (MiB); must be valid for chosen CPU."
  default     = "512"
}

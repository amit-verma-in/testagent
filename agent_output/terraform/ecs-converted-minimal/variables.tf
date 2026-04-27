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
  default     = "sample-ecs-min"
}

variable "vpc_id" {
  type        = string
  description = "VPC for the service."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnets for tasks. For this minimal template, use subnets with a route to an internet gateway if AssignPublicIp is ENABLED (default)."
}

variable "container_image" {
  type    = string
  default = "public.ecr.aws/docker/library/nginx:alpine"
}

variable "container_port" {
  type    = number
  default = 80
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "assign_public_ip" {
  type        = string
  description = "ENABLED = tasks get a public IP (simple demo). DISABLED requires NAT for pulls."
  default     = "ENABLED"
}

# Generated from CloudFormation Outputs.

output "cluster_name" {
  value       = aws_ecs_cluster.ecs_cluster.name
}

output "service_arn" {
  value       = aws_ecs_service.ecs_service.id
}

output "task_security_group_id" {
  description = "Security group on tasks (ingress open to 0.0.0.0/0 in this sample)."
  value       = aws_security_group.task_security_group.id
}

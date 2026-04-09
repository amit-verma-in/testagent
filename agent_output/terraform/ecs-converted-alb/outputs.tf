# Module-based outputs (aligned with main.tf).

output "cluster_name" {
  description = "ECS cluster name."
  value       = module.ecs_cluster.name
}

output "service_name" {
  description = "ECS service name."
  value       = module.ecs_service.name
}

output "load_balancer_dns_name" {
  description = "DNS name of the ALB (open in browser on port 80)."
  value       = module.alb.lb_dns_name
}

output "stack_name" {
  description = "Stack name variable."
  value       = var.stack_name
}

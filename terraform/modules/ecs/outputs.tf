output "cluster_id" {
  description = "ECS Cluster ID"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "ECS Cluster name"
  value       = aws_ecs_cluster.main.name
}

output "service_names" {
  description = "Map of service key to ECS service name"
  value       = { for k, v in aws_ecs_service.services : k => v.name }
}

output "task_definition_arns" {
  description = "Map of service key to task definition ARN"
  value       = { for k, v in aws_ecs_task_definition.services : k => v.arn }
}

output "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  value       = aws_security_group.ecs_tasks.id
}

output "service_discovery_namespace_id" {
  description = "Service discovery namespace ID"
  value       = aws_service_discovery_private_dns_namespace.main.id
}

output "log_group_names" {
  description = "Map of service key to CloudWatch log group name"
  value       = { for k, v in aws_cloudwatch_log_group.services : k => v.name }
}

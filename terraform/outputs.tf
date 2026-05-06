# ─────────────────────────────────────────────────────
# Root Outputs
# ─────────────────────────────────────────────────────

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "alb_dns_name" {
  description = "ALB DNS name — use this to access the API Gateway"
  value       = module.alb.alb_dns_name
}

output "ecr_repository_urls" {
  description = "ECR repository URLs for each service"
  value       = module.ecr.repository_urls
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_service_names" {
  description = "ECS service names"
  value       = module.ecs.service_names
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log group names per service"
  value       = module.ecs.log_group_names
}

output "api_url" {
  description = "Full API URL"
  value       = "http://${module.alb.alb_dns_name}"
}

# ─────────────────────────────────────────────────────
# ECS Module Variables
# ─────────────────────────────────────────────────────

variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "ALB security group ID (for ECS ingress rules)"
  type        = string
}

variable "api_gateway_target_group_arn" {
  description = "Target group ARN for API Gateway service"
  type        = string
}

variable "ecr_repository_urls" {
  description = "Map of service name to ECR repository URL"
  type        = map(string)
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "tags" {
  type    = map(string)
  default = {}
}

# ── Service Configuration ────────────────────────────

variable "services" {
  description = "Configuration for each microservice"
  type = map(object({
    cpu            = number
    memory         = number
    container_port = number
    desired_count  = number
    environment    = list(object({
      name  = string
      value = string
    }))
  }))
}

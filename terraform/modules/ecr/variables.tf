# ─────────────────────────────────────────────────────
# ECR Module — Container Registry
# Creates one ECR repository per microservice with
# lifecycle policies for image cleanup.
# ─────────────────────────────────────────────────────

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "services" {
  description = "List of service names to create repositories for"
  type        = list(string)
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}

# ─────────────────────────────────────────────────────
# ALB Module Variables
# ─────────────────────────────────────────────────────

variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  description = "VPC ID for security groups"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB placement"
  type        = list(string)
}

variable "health_check_path" {
  description = "Health check path for default target group"
  type        = string
  default     = "/health"
}

variable "tags" {
  type    = map(string)
  default = {}
}

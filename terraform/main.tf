# ─────────────────────────────────────────────────────
# Damolak Microservices — Root Terraform Configuration
#
# Orchestrates all modules to deploy a production-ready
# 5-service microservices platform on AWS ECS Fargate.
# ─────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }

  # Uncomment for remote state (recommended for teams):
  # backend "s3" {
  #   bucket         = "damolak-terraform-state"
  #   key            = "production/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "damolak-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── Local Values ─────────────────────────────────────

locals {
  services = ["api-gateway", "auth-service", "data-service", "processing-service", "notification-service"]

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ── Module: VPC ──────────────────────────────────────

module "vpc" {
  source = "./modules/vpc"

  project_name        = var.project_name
  environment         = var.environment
  vpc_cidr            = var.vpc_cidr
  availability_zones  = var.availability_zones
  public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]
  tags                = local.common_tags
}

# ── Module: ECR ──────────────────────────────────────

module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
  services     = local.services
  tags         = local.common_tags
}

# ── Module: ALB ──────────────────────────────────────

module "alb" {
  source = "./modules/alb"

  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  health_check_path = "/health"
  tags              = local.common_tags
}

# ── Module: ECS ──────────────────────────────────────

module "ecs" {
  source = "./modules/ecs"

  project_name                = var.project_name
  environment                 = var.environment
  vpc_id                      = module.vpc.vpc_id
  private_subnet_ids          = module.vpc.private_subnet_ids
  alb_security_group_id       = module.alb.alb_security_group_id
  api_gateway_target_group_arn = module.alb.api_gateway_target_group_arn
  ecr_repository_urls         = module.ecr.repository_urls
  aws_region                  = var.aws_region
  tags                        = local.common_tags

  services = {
    "api-gateway" = {
      cpu            = 256
      memory         = 512
      container_port = 3000
      desired_count  = 2
      environment = [
        { name = "NODE_ENV", value = "production" },
        { name = "PORT", value = "3000" },
        { name = "AUTH_SERVICE_URL", value = "http://auth-service.damolak.local:8080" },
        { name = "DATA_SERVICE_URL", value = "http://data-service.damolak.local:8000" },
        { name = "PROCESSING_SERVICE_URL", value = "http://processing-service.damolak.local:8081" },
        { name = "NOTIFICATION_SERVICE_URL", value = "http://notification-service.damolak.local:5000" },
      ]
    }

    "auth-service" = {
      cpu            = 512
      memory         = 1024
      container_port = 8080
      desired_count  = 2
      environment = [
        { name = "SPRING_PROFILES_ACTIVE", value = "production" },
        { name = "JWT_SECRET", value = "production-secret-change-me-to-real-secret-min-256-bits" },
      ]
    }

    "data-service" = {
      cpu            = 256
      memory         = 512
      container_port = 8000
      desired_count  = 2
      environment = [
        { name = "ENVIRONMENT", value = "production" },
        { name = "PORT", value = "8000" },
        { name = "PROCESSING_SERVICE_URL", value = "http://processing-service.damolak.local:8081" },
        { name = "NOTIFICATION_SERVICE_URL", value = "http://notification-service.damolak.local:5000" },
      ]
    }

    "processing-service" = {
      cpu            = 256
      memory         = 512
      container_port = 8081
      desired_count  = 2
      environment = [
        { name = "PORT", value = "8081" },
      ]
    }

    "notification-service" = {
      cpu            = 256
      memory         = 512
      container_port = 5000
      desired_count  = 1
      environment = [
        { name = "PORT", value = "5000" },
        { name = "LOG_LEVEL", value = "INFO" },
      ]
    }
  }
}

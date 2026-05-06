# ─────────────────────────────────────────────────────
# ECS Module — Fargate Cluster, Tasks & Services
#
# Creates:
# - ECS Cluster with Container Insights
# - CloudWatch log groups per service
# - IAM roles (task execution + task)
# - Security group for ECS tasks
# - Task definitions per service
# - ECS services per service
# - Service discovery namespace for inter-service communication
#
# Design Decision: Each service gets its own task definition
# and ECS service for independent scaling and deployment.
# ─────────────────────────────────────────────────────

locals {
  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "ecs"
  })
}

# ── ECS Cluster ──────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-cluster"
  })
}

# ── Service Discovery Namespace ──────────────────────
# Enables services to find each other by DNS name
# e.g., auth-service.damolak.local

resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "${var.project_name}.local"
  description = "Service discovery namespace for ${var.project_name}"
  vpc         = var.vpc_id

  tags = local.common_tags
}

resource "aws_service_discovery_service" "services" {
  for_each = var.services

  name = each.key

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# ── CloudWatch Log Groups ───────────────────────────

resource "aws_cloudwatch_log_group" "services" {
  for_each = var.services

  name              = "/ecs/${var.project_name}-${var.environment}/${each.key}"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Name    = "${each.key}-logs"
    Service = each.key
  })
}

# ── IAM: Task Execution Role ────────────────────────
# Used by ECS agent to pull images and push logs

resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-${var.environment}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ── IAM: Task Role ──────────────────────────────────
# Used by application code inside the container

resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-${var.environment}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "ecs_task_cloudwatch" {
  name = "${var.project_name}-${var.environment}-task-cw"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ]
      Resource = "*"
    }]
  })
}

# ── Security Group: ECS Tasks ────────────────────────

resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.project_name}-${var.environment}-ecs-"
  description = "Security group for ECS Fargate tasks"
  vpc_id      = var.vpc_id

  # Allow inbound from ALB
  ingress {
    description     = "From ALB"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }

  # Allow inbound from other ECS tasks (inter-service)
  ingress {
    description = "Inter-service communication"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
  }

  # Outbound: all (for NAT gateway, ECR pull, etc.)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-ecs-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ── Task Definitions ────────────────────────────────

resource "aws_ecs_task_definition" "services" {
  for_each = var.services

  family                   = "${var.project_name}-${var.environment}-${each.key}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = each.key
    image     = "${var.ecr_repository_urls[each.key]}:latest"
    essential = true

    portMappings = [{
      containerPort = each.value.container_port
      protocol      = "tcp"
    }]

    environment = each.value.environment

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.services[each.key].name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = each.key
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:${each.value.container_port}/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = merge(local.common_tags, {
    Service = each.key
  })
}

# ── ECS Services ────────────────────────────────────

resource "aws_ecs_service" "services" {
  for_each = var.services

  name            = "${var.project_name}-${var.environment}-${each.key}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.services[each.key].arn
  desired_count   = each.value.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  # Only the API Gateway gets attached to the ALB
  dynamic "load_balancer" {
    for_each = each.key == "api-gateway" ? [1] : []
    content {
      target_group_arn = var.api_gateway_target_group_arn
      container_name   = each.key
      container_port   = each.value.container_port
    }
  }

  service_registries {
    registry_arn = aws_service_discovery_service.services[each.key].arn
  }

  # Allow ECS to manage deployment
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  # Ensure new task definition is used on deploy
  force_new_deployment = true

  tags = merge(local.common_tags, {
    Service = each.key
  })

  depends_on = [aws_iam_role_policy_attachment.ecs_execution]
}

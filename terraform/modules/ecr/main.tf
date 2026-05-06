# ─────────────────────────────────────────────────────
# ECR Module — Main Resources
# ─────────────────────────────────────────────────────

locals {
  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "ecr"
  })
}

resource "aws_ecr_repository" "services" {
  for_each = toset(var.services)

  name                 = "${var.project_name}-${var.environment}-${each.key}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-${var.environment}-${each.key}"
    Service = each.key
  })
}

# Lifecycle policy — keep last 10 images, expire untagged after 7 days
resource "aws_ecr_lifecycle_policy" "cleanup" {
  for_each   = toset(var.services)
  repository = aws_ecr_repository.services[each.key].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep only last 10 tagged images"
        selection = {
          tagStatus   = "tagged"
          tagPrefixList = ["v", "latest", "main"]
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

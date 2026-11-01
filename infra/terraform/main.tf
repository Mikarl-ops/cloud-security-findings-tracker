resource "terraform_data" "approval" {
  lifecycle {
    precondition {
      condition     = var.deployment_approved
      error_message = "Live deployment is disabled. Use mocked tests for local validation. Owner approval and the deployment checklist are required for AWS work."
    }
    precondition {
      condition     = var.desired_count == 0 || length(var.allowed_client_cidrs) > 0
      error_message = "Task activation requires an explicit HTTPS client allowlist."
    }
  }
}

locals {
  name = var.environment
  zones = {
    for index, zone in var.availability_zones : zone => index
  }
  account_root = "arn:aws:iam::${var.aws_account_id}:root"
  log_prefix   = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/csft/${local.name}/"
  ecs_trust = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = var.aws_account_id }
        ArnLike      = { "aws:SourceArn" = "arn:aws:ecs:${var.aws_region}:${var.aws_account_id}:*" }
      }
    }]
  })
}

resource "aws_kms_key" "application" {
  description             = "Encryption for ${local.name} synthetic application data and logs"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AccountIAMDelegation"
        Effect    = "Allow"
        Principal = { AWS = local.account_root }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "EncryptedLogs"
        Effect    = "Allow"
        Principal = { Service = "logs.${var.aws_region}.amazonaws.com" }
        Action    = ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"]
        Resource  = "*"
        Condition = { ArnLike = { "kms:EncryptionContext:aws:logs:arn" = ["${local.log_prefix}*", "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/rds/instance/${local.name}/postgresql"] } }
      }
    ]
  })
  depends_on = [terraform_data.approval]
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_kms_alias" "application" {
  name          = "alias/${local.name}"
  target_key_id = aws_kms_key.application.key_id
}

resource "aws_cloudwatch_log_group" "application" {
  for_each          = toset(["tasks", "flow"])
  name              = "/csft/${local.name}/${each.key}"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.application.arn
}

resource "aws_ecr_repository" "application" {
  for_each             = toset(["api", "frontend"])
  name                 = "${local.name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.application.arn
  }
}

resource "aws_ecr_lifecycle_policy" "application" {
  for_each   = aws_ecr_repository.application
  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Remove untagged images after seven days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 7
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_secretsmanager_secret" "application" {
  name                    = "${local.name}/application"
  description             = "Populate DATABASE_URL and SECRET_KEY outside Terraform after approval; no secret values are managed here."
  kms_key_id              = aws_kms_key.application.arn
  recovery_window_in_days = 30
}

resource "aws_iam_role" "execution" {
  name               = "${local.name}-execution"
  assume_role_policy = local.ecs_trust
  depends_on         = [terraform_data.approval]
}

resource "aws_iam_role_policy" "execution" {
  name = "pull-log-and-read-application-secret"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ECRAuthentication"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"]
        Resource = [for repository in aws_ecr_repository.application : repository.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.application["tasks"].arn}:*"
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.application.arn
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = aws_kms_key.application.arn
        Condition = {
          StringEquals = {
            "kms:ViaService"                  = "secretsmanager.${var.aws_region}.amazonaws.com"
            "kms:EncryptionContext:SecretARN" = aws_secretsmanager_secret.application.arn
          }
        }
      }
    ]
  })
}

resource "aws_iam_role" "task" {
  name               = "${local.name}-task"
  assume_role_policy = local.ecs_trust
  depends_on         = [terraform_data.approval]
}

resource "aws_ecs_cluster" "application" {
  name = local.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  depends_on = [terraform_data.approval]
}

resource "aws_ecs_task_definition" "application" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  volume {
    name = "api-tmp"
  }
  volume {
    name = "frontend-tmp"
  }
  container_definitions = jsonencode([
    {
      name                   = "api"
      image                  = var.api_image
      essential              = true
      user                   = "10001:10001"
      readonlyRootFilesystem = true
      cpu                    = 384
      memory                 = 768
      portMappings           = [{ containerPort = 8000, protocol = "tcp" }]
      linuxParameters        = { initProcessEnabled = true, capabilities = { drop = ["ALL"] } }
      mountPoints            = [{ sourceVolume = "api-tmp", containerPath = "/tmp", readOnly = false }]
      environment = [
        { name = "APP_ENV", value = "production" },
        { name = "SESSION_COOKIE_SECURE", value = "true" }
      ]
      secrets = [
        { name = "DATABASE_URL", valueFrom = "${aws_secretsmanager_secret.application.arn}:DATABASE_URL::" },
        { name = "SECRET_KEY", valueFrom = "${aws_secretsmanager_secret.application.arn}:SECRET_KEY::" }
      ]
      healthCheck = {
        command     = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=3)"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.application["tasks"].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }
    },
    {
      name                   = "frontend"
      image                  = var.frontend_image
      essential              = true
      user                   = "10001:10001"
      readonlyRootFilesystem = true
      cpu                    = 128
      memory                 = 256
      portMappings           = [{ containerPort = 8080, protocol = "tcp" }]
      linuxParameters        = { initProcessEnabled = true, capabilities = { drop = ["ALL"] } }
      mountPoints            = [{ sourceVolume = "frontend-tmp", containerPath = "/tmp", readOnly = false }]
      dependsOn              = [{ containerName = "api", condition = "HEALTHY" }]
      healthCheck = {
        command     = ["CMD-SHELL", "wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.application["tasks"].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "frontend"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "application" {
  name                               = local.name
  cluster                            = aws_ecs_cluster.application.id
  task_definition                    = aws_ecs_task_definition.application.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  platform_version                   = "1.4.0"
  enable_execute_command             = false
  health_check_grace_period_seconds  = 60
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = [for subnet in aws_subnet.application : subnet.id]
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.application.arn
    container_name   = "frontend"
    container_port   = 8080
  }
  depends_on = [
    aws_lb_listener.https,
    aws_iam_role_policy.execution,
    aws_vpc_endpoint.interface,
    aws_vpc_endpoint.s3,
    aws_vpc_security_group_egress_rule.endpoint,
    aws_vpc_security_group_egress_rule.database,
    aws_vpc_security_group_egress_rule.image_layers
  ]
}

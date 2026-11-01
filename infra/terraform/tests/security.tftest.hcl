# Every run plans against an AWS mock. No apply run and no real AWS provider are permitted here.
mock_provider "aws" {
  override_during = plan
  mock_resource "aws_kms_key" {
    defaults = {
      arn    = "arn:aws:kms:ap-southeast-1:000000000000:key/00000000-0000-0000-0000-000000000000"
      key_id = "00000000-0000-0000-0000-000000000000"
    }
  }
  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:ap-southeast-1:000000000000:log-group:/csft/csft-demo/tasks" }
  }
  mock_resource "aws_secretsmanager_secret" {
    defaults = { arn = "arn:aws:secretsmanager:ap-southeast-1:000000000000:secret:csft-demo/application-000000" }
  }
  mock_resource "aws_route_table" {
    defaults = { route = [] }
  }
}

override_resource {
  target          = aws_security_group.task
  override_during = plan
  values          = { id = "sg-00000000000000001" }
}

override_resource {
  target          = aws_security_group.edge
  override_during = plan
  values          = { id = "sg-00000000000000002" }
}

override_resource {
  target          = aws_security_group.endpoint
  override_during = plan
  values          = { id = "sg-00000000000000003" }
}

override_resource {
  target          = aws_security_group.database
  override_during = plan
  values          = { id = "sg-00000000000000004" }
}

override_resource {
  target          = aws_ecr_repository.application["api"]
  override_during = plan
  values          = { arn = "arn:aws:ecr:ap-southeast-1:000000000000:repository/csft-demo/api" }
}

override_resource {
  target          = aws_ecr_repository.application["frontend"]
  override_during = plan
  values          = { arn = "arn:aws:ecr:ap-southeast-1:000000000000:repository/csft-demo/frontend" }
}

run "deployment_guard" {
  command         = plan
  expect_failures = [terraform_data.approval]
}

run "private_data_and_restricted_tasks" {
  command = plan
  variables {
    deployment_approved = true
  }
  assert {
    condition = (
      alltrue([for subnet in aws_subnet.application : !subnet.map_public_ip_on_launch]) &&
      alltrue([for subnet in aws_subnet.database : !subnet.map_public_ip_on_launch]) &&
      !aws_ecs_service.application.network_configuration[0].assign_public_ip &&
      aws_ecs_service.application.desired_count == 0 &&
      length(aws_route_table.application.route) == 0 &&
      length(aws_route_table.database.route) == 0
    )
    error_message = "Tasks and the database must stay private without a default internet route; tasks start disabled."
  }
  assert {
    condition = (
      !aws_db_instance.application.publicly_accessible &&
      aws_db_instance.application.storage_encrypted &&
      aws_db_instance.application.manage_master_user_password &&
      aws_db_instance.application.deletion_protection &&
      !aws_db_instance.application.skip_final_snapshot &&
      aws_db_instance.application.backup_retention_period >= 7 &&
      aws_db_instance.application.multi_az &&
      one(aws_db_parameter_group.application.parameter).value == "1"
    )
    error_message = "Database isolation, encryption, managed credentials, TLS, backups, and deletion protection are required."
  }
  assert {
    condition = alltrue([
      for container in jsondecode(aws_ecs_task_definition.application.container_definitions) :
      container.readonlyRootFilesystem &&
      container.user == "10001:10001" &&
      contains(container.linuxParameters.capabilities.drop, "ALL") &&
      !try(container.privileged, false) &&
      strcontains(container.image, "@sha256:")
    ])
    error_message = "Both containers require non-root execution, read-only roots, dropped capabilities, and immutable images."
  }
  assert {
    condition = (
      aws_lb_listener.https.protocol == "HTTPS" &&
      aws_lb_listener.https.port == 443 &&
      aws_vpc_security_group_ingress_rule.frontend.from_port == 8080 &&
      aws_vpc_security_group_ingress_rule.database.from_port == 5432 &&
      aws_vpc_security_group_ingress_rule.database.referenced_security_group_id == aws_security_group.task.id &&
      length(aws_vpc_security_group_ingress_rule.https) == 0
    )
    error_message = "Only HTTPS at the edge, frontend traffic from ALB, and task-to-database traffic are allowed; no client is allowed by default."
  }
  assert {
    condition = (
      aws_kms_key.application.enable_key_rotation &&
      alltrue([for group in aws_cloudwatch_log_group.application : group.retention_in_days == 30 && group.kms_key_id == aws_kms_key.application.arn]) &&
      alltrue([for repository in aws_ecr_repository.application : repository.image_tag_mutability == "IMMUTABLE" && repository.image_scanning_configuration[0].scan_on_push]) &&
      aws_s3_bucket_public_access_block.access_logs.block_public_policy &&
      aws_s3_bucket_public_access_block.access_logs.restrict_public_buckets
    )
    error_message = "Logs and registries need encryption/retention and immutable scanned images; log storage must remain private."
  }
  assert {
    condition = (
      jsondecode(aws_iam_role.task.assume_role_policy).Statement[0].Condition.StringEquals["aws:SourceAccount"] == var.aws_account_id &&
      alltrue([for statement in jsondecode(aws_iam_role_policy.execution.policy).Statement :
        statement.Resource != "*" || try(statement.Sid == "ECRAuthentication", false)
      ]) &&
      length(jsondecode(aws_ecs_task_definition.application.container_definitions)[0].secrets) == 2 &&
      !aws_ecs_service.application.enable_execute_command
    )
    error_message = "Execution permissions must stay scoped except ECR authentication; tasks receive only the two application secrets and no ECS Exec access."
  }
}

run "reject_public_wide_ingress" {
  command = plan
  variables {
    deployment_approved  = true
    allowed_client_cidrs = ["0.0.0.0/0"]
  }
  expect_failures = [var.allowed_client_cidrs]
}

run "reject_mutable_images" {
  command = plan
  variables {
    deployment_approved = true
    api_image           = "000000000000.dkr.ecr.ap-southeast-1.amazonaws.com/csft-demo/api:latest"
  }
  expect_failures = [var.api_image]
}

run "reject_duplicate_zones" {
  command = plan
  variables {
    deployment_approved = true
    availability_zones  = ["ap-southeast-1a", "ap-southeast-1a"]
  }
  expect_failures = [var.availability_zones]
}

run "activation_requires_client_allowlist" {
  command = plan
  variables {
    deployment_approved = true
    desired_count       = 1
  }
  expect_failures = [terraform_data.approval]
}

run "reviewed_activation_shape" {
  command = plan
  variables {
    deployment_approved  = true
    desired_count        = 1
    allowed_client_cidrs = ["203.0.113.10/32"]
  }
  assert {
    condition = (
      aws_ecs_service.application.desired_count == 1 &&
      length(aws_vpc_security_group_ingress_rule.https) == 1 &&
      aws_vpc_security_group_ingress_rule.https["203.0.113.10/32"].from_port == 443
    )
    error_message = "The reviewed activation shape must retain explicit HTTPS client restriction."
  }
}

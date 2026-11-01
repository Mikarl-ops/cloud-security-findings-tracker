resource "aws_vpc" "application" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = local.name }
  depends_on           = [terraform_data.approval]
}

resource "aws_default_security_group" "deny" {
  vpc_id = aws_vpc.application.id
  tags   = { Name = "${local.name}-default-deny" }
}

resource "aws_subnet" "edge" {
  for_each                = local.zones
  vpc_id                  = aws_vpc.application.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(aws_vpc.application.cidr_block, 8, each.value)
  map_public_ip_on_launch = false
  tags                    = { Name = "${local.name}-edge-${each.value}" }
}

resource "aws_subnet" "application" {
  for_each                = local.zones
  vpc_id                  = aws_vpc.application.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(aws_vpc.application.cidr_block, 8, each.value + 10)
  map_public_ip_on_launch = false
  tags                    = { Name = "${local.name}-app-${each.value}" }
}

resource "aws_subnet" "database" {
  for_each                = local.zones
  vpc_id                  = aws_vpc.application.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(aws_vpc.application.cidr_block, 8, each.value + 20)
  map_public_ip_on_launch = false
  tags                    = { Name = "${local.name}-db-${each.value}" }
}

resource "aws_internet_gateway" "edge" {
  vpc_id = aws_vpc.application.id
}

resource "aws_route_table" "edge" {
  vpc_id = aws_vpc.application.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.edge.id
  }
}

resource "aws_route_table" "application" {
  vpc_id = aws_vpc.application.id
}

resource "aws_route_table" "database" {
  vpc_id = aws_vpc.application.id
}

resource "aws_route_table_association" "edge" {
  for_each       = aws_subnet.edge
  subnet_id      = each.value.id
  route_table_id = aws_route_table.edge.id
}

resource "aws_route_table_association" "application" {
  for_each       = aws_subnet.application
  subnet_id      = each.value.id
  route_table_id = aws_route_table.application.id
}

resource "aws_route_table_association" "database" {
  for_each       = aws_subnet.database
  subnet_id      = each.value.id
  route_table_id = aws_route_table.database.id
}

resource "aws_security_group" "edge" {
  name        = "${local.name}-edge"
  description = "Allowlisted HTTPS clients to the frontend only"
  vpc_id      = aws_vpc.application.id
}

resource "aws_security_group" "task" {
  name        = "${local.name}-task"
  description = "Frontend from ALB; private service endpoints and PostgreSQL egress only"
  vpc_id      = aws_vpc.application.id
}

resource "aws_security_group" "endpoint" {
  name        = "${local.name}-endpoint"
  description = "AWS private endpoint HTTPS from application tasks"
  vpc_id      = aws_vpc.application.id
}

resource "aws_security_group" "database" {
  name        = "${local.name}-database"
  description = "PostgreSQL from the application task only"
  vpc_id      = aws_vpc.application.id
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  for_each          = var.allowed_client_cidrs
  security_group_id = aws_security_group.edge.id
  description       = "Approved demonstration clients"
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_ingress_rule" "frontend" {
  security_group_id            = aws_security_group.task.id
  description                  = "ALB to frontend reverse proxy"
  referenced_security_group_id = aws_security_group.edge.id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

resource "aws_vpc_security_group_egress_rule" "frontend" {
  security_group_id            = aws_security_group.edge.id
  description                  = "ALB to frontend reverse proxy"
  referenced_security_group_id = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

resource "aws_vpc_security_group_ingress_rule" "endpoint" {
  security_group_id            = aws_security_group.endpoint.id
  description                  = "Task access to private AWS endpoints"
  referenced_security_group_id = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}

resource "aws_vpc_security_group_egress_rule" "endpoint" {
  security_group_id            = aws_security_group.task.id
  description                  = "HTTPS to private AWS endpoints"
  referenced_security_group_id = aws_security_group.endpoint.id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}

resource "aws_vpc_security_group_ingress_rule" "database" {
  security_group_id            = aws_security_group.database.id
  description                  = "Application PostgreSQL access"
  referenced_security_group_id = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_egress_rule" "database" {
  security_group_id            = aws_security_group.task.id
  description                  = "Application PostgreSQL access"
  referenced_security_group_id = aws_security_group.database.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_endpoint" "interface" {
  for_each            = toset(["ecr.api", "ecr.dkr", "logs", "secretsmanager"])
  vpc_id              = aws_vpc.application.id
  service_name        = "com.amazonaws.${var.aws_region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [for subnet in aws_subnet.application : subnet.id]
  security_group_ids  = [aws_security_group.endpoint.id]
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.application.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.application.id]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = ["s3:GetObject"]
      Resource  = "arn:aws:s3:::prod-${var.aws_region}-starport-layer-bucket/*"
    }]
  })
}

resource "aws_vpc_security_group_egress_rule" "image_layers" {
  security_group_id = aws_security_group.task.id
  description       = "HTTPS to ECR image layers in regional S3"
  prefix_list_id    = aws_vpc_endpoint.s3.prefix_list_id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_iam_role" "flow" {
  name = "${local.name}-flow"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "vpc-flow-logs.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = { StringEquals = { "aws:SourceAccount" = var.aws_account_id } }
    }]
  })
  depends_on = [terraform_data.approval]
}

resource "aws_iam_role_policy" "flow" {
  role = aws_iam_role.flow.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"]
      Resource = "${aws_cloudwatch_log_group.application["flow"].arn}:*"
    }]
  })
}

resource "aws_flow_log" "application" {
  vpc_id               = aws_vpc.application.id
  traffic_type         = "ALL"
  log_destination_type = "cloud-watch-logs"
  log_destination      = aws_cloudwatch_log_group.application["flow"].arn
  iam_role_arn         = aws_iam_role.flow.arn
  depends_on           = [aws_iam_role_policy.flow]
}

resource "aws_s3_bucket" "access_logs" {
  bucket_prefix = "${local.name}-alb-"
  force_destroy = false
  depends_on    = [terraform_data.approval]
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket                  = aws_s3_bucket.access_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ALB log delivery supports SSE-S3 only. Private bucket, TLS-only access, and bounded retention apply.
# Review before deployment or 2026-11-30; see docs/decisions/0003-optional-ecs-foundation.md.
#trivy:ignore:AVD-AWS-0132:exp:2026-11-30
resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  rule {
    id     = "bounded-log-retention"
    status = "Enabled"
    filter {}
    expiration {
      days = 30
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
  depends_on = [aws_s3_bucket_versioning.access_logs]
}

resource "aws_s3_bucket_policy" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "ALBLogDelivery"
        Effect    = "Allow"
        Principal = { Service = "logdelivery.elasticloadbalancing.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.access_logs.arn}/AWSLogs/${var.aws_account_id}/*"
      },
      {
        Sid       = "RequireTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.access_logs.arn, "${aws_s3_bucket.access_logs.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      }
    ]
  })
}

# Deliberate HTTPS edge with no clients allowed by default; only approved /24-or-narrower CIDRs can enter.
# Review before deployment or 2026-11-30; see docs/decisions/0003-optional-ecs-foundation.md.
#trivy:ignore:AVD-AWS-0053:exp:2026-11-30
resource "aws_lb" "application" {
  name                       = local.name
  internal                   = false
  load_balancer_type         = "application"
  subnets                    = [for subnet in aws_subnet.edge : subnet.id]
  security_groups            = [aws_security_group.edge.id]
  drop_invalid_header_fields = true
  enable_deletion_protection = true
  desync_mitigation_mode     = "strictest"
  access_logs {
    bucket  = aws_s3_bucket.access_logs.id
    enabled = true
  }
  depends_on = [
    aws_s3_bucket_policy.access_logs,
    aws_s3_bucket_public_access_block.access_logs,
    aws_s3_bucket_server_side_encryption_configuration.access_logs,
    aws_s3_bucket_ownership_controls.access_logs,
    aws_internet_gateway.edge,
    aws_route_table_association.edge
  ]
}

resource "aws_lb_target_group" "application" {
  name        = local.name
  port        = 8080
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.application.id
  health_check {
    path                = "/api/v1/health/ready"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.application.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.application.arn
  }
}

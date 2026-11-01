resource "aws_db_subnet_group" "application" {
  name       = local.name
  subnet_ids = [for subnet in aws_subnet.database : subnet.id]
}

resource "aws_db_parameter_group" "application" {
  name   = local.name
  family = "postgres18"
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
  depends_on = [terraform_data.approval]
}

resource "aws_cloudwatch_log_group" "database" {
  name              = "/aws/rds/instance/${local.name}/postgresql"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.application.arn
}

resource "aws_db_instance" "application" {
  identifier                            = local.name
  engine                                = "postgres"
  engine_version                        = var.db_engine_version
  instance_class                        = "db.t4g.micro"
  allocated_storage                     = 20
  max_allocated_storage                 = 100
  storage_type                          = "gp3"
  storage_encrypted                     = true
  kms_key_id                            = aws_kms_key.application.arn
  db_name                               = "tracker"
  username                              = "tracker_admin"
  manage_master_user_password           = true
  master_user_secret_kms_key_id         = aws_kms_key.application.arn
  iam_database_authentication_enabled   = true
  db_subnet_group_name                  = aws_db_subnet_group.application.name
  parameter_group_name                  = aws_db_parameter_group.application.name
  vpc_security_group_ids                = [aws_security_group.database.id]
  publicly_accessible                   = false
  multi_az                              = true
  backup_retention_period               = 7
  backup_window                         = "17:00-18:00"
  maintenance_window                    = "sun:18:00-sun:19:00"
  auto_minor_version_upgrade            = true
  allow_major_version_upgrade           = false
  apply_immediately                     = false
  deletion_protection                   = true
  skip_final_snapshot                   = false
  final_snapshot_identifier             = var.final_snapshot_identifier
  copy_tags_to_snapshot                 = true
  enabled_cloudwatch_logs_exports       = ["postgresql"]
  performance_insights_enabled          = true
  performance_insights_kms_key_id       = aws_kms_key.application.arn
  performance_insights_retention_period = 7
  database_insights_mode                = "standard"
  depends_on                            = [aws_cloudwatch_log_group.database]
}

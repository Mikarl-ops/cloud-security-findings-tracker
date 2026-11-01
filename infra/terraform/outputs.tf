output "image_repositories" {
  description = "Repository locations only; this configuration does not build or publish images."
  value       = { for name, repository in aws_ecr_repository.application : name => repository.repository_url }
}

output "application_secret_arn" {
  description = "Secret envelope only. Populate approved runtime credentials out of band."
  value       = aws_secretsmanager_secret.application.arn
}

output "database_address" {
  description = "Private database hostname; not a credential."
  value       = aws_db_instance.application.address
}

output "load_balancer_dns_name" {
  description = "Connect using the reviewed certificate hostname and DNS configuration, not this raw hostname."
  value       = aws_lb.application.dns_name
}

variable "deployment_approved" {
  description = "Accidental-use guard only. Live AWS work also requires explicit owner approval and the deployment checklist."
  type        = bool
  default     = false
}

variable "environment" {
  description = "Unique short name for a reviewed demonstration environment."
  type        = string
  default     = "csft-demo"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.environment))
    error_message = "Use 3-20 lowercase letters, digits, or hyphens, starting with a letter."
  }
}

variable "aws_region" {
  description = "Owner-selected AWS commercial region; no live region is selected by this repository."
  type        = string
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "Supply an AWS commercial region."
  }
}

variable "aws_account_id" {
  description = "Expected account ID, used to restrict the provider and scope resource policies."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Supply a 12-digit account ID."
  }
}

variable "availability_zones" {
  description = "Two reviewed AZ names in the chosen region, in stable order."
  type        = list(string)
  validation {
    condition = (
      length(var.availability_zones) == 2 &&
      length(distinct(var.availability_zones)) == 2 &&
      alltrue([for az in var.availability_zones : startswith(az, var.aws_region)])
    )
    error_message = "Supply two distinct availability zones in aws_region."
  }
}

variable "allowed_client_cidrs" {
  description = "Explicit IPv4 HTTPS allowlist. Public-wide access is rejected."
  type        = set(string)
  default     = []
  validation {
    condition = alltrue([
      for cidr in var.allowed_client_cidrs :
      can(cidrnetmask(cidr)) && try(tonumber(split("/", cidr)[1]) >= 24, false)
    ])
    error_message = "Use IPv4 CIDRs with prefix /24 or narrower; do not expose the demonstration broadly."
  }
}

variable "certificate_arn" {
  description = "Existing, validated ACM certificate in the selected region/account; creation and DNS validation are separate prerequisites."
  type        = string
  validation {
    condition     = startswith(var.certificate_arn, "arn:aws:acm:${var.aws_region}:${var.aws_account_id}:certificate/")
    error_message = "The ACM certificate must belong to the selected region and account."
  }
}

variable "api_image" {
  description = "Reviewed production API image in this environment's ECR repository, pinned by digest. Development images are unsuitable."
  type        = string
  validation {
    condition     = can(regex("^${var.aws_account_id}[.]dkr[.]ecr[.]${var.aws_region}[.]amazonaws[.]com/${var.environment}/api@sha256:[a-f0-9]{64}$", var.api_image))
    error_message = "Supply the production API repository URI pinned to a SHA-256 digest."
  }
}

variable "frontend_image" {
  description = "Reviewed static UI/reverse-proxy image pinned by digest. Vite's development server is unsuitable."
  type        = string
  validation {
    condition     = can(regex("^${var.aws_account_id}[.]dkr[.]ecr[.]${var.aws_region}[.]amazonaws[.]com/${var.environment}/frontend@sha256:[a-f0-9]{64}$", var.frontend_image))
    error_message = "Supply the production frontend repository URI pinned to a SHA-256 digest."
  }
}

variable "db_engine_version" {
  description = "PostgreSQL 18 patch verified as available in the selected RDS region before deployment."
  type        = string
  validation {
    condition     = can(regex("^18[.][0-9]+$", var.db_engine_version))
    error_message = "Use a verified PostgreSQL 18 patch release."
  }
}

variable "final_snapshot_identifier" {
  description = "Unique final snapshot name approved with the persistent-data retention plan."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,62}[a-z0-9]$", var.final_snapshot_identifier)) && !strcontains(var.final_snapshot_identifier, "--")
    error_message = "Use a unique 4-64 character RDS snapshot identifier without consecutive or trailing hyphens."
  }
}

variable "desired_count" {
  description = "Defaults to zero. Task activation is a separate approval after images, secrets, migrations, and public-exposure controls are reviewed."
  type        = number
  default     = 0
  validation {
    condition     = contains([0, 1, 2], var.desired_count)
    error_message = "Use zero, one, or two demonstration tasks."
  }
}

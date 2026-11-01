# Optional ECS Terraform foundation

This configuration defines the optional ECS Fargate path for code review. No resources have been provisioned and no images or secrets have been published. The deployment guard defaults to false, task count defaults to zero, and no client CIDRs are allowed by default. These defaults do not authorize a deployment.

Read [ADR 0003](../../docs/decisions/0003-optional-ecs-foundation.md) for architecture, IAM and network boundaries, scanner exceptions, and prerequisites.

## Reproduce validation

Use Terraform **1.17.1**, the committed AWS **6.71.0** provider lock, and Trivy **0.76.1**. From this directory:

```text
terraform fmt -check -recursive
terraform init -backend=false -input=false -lockfile=readonly
terraform validate
terraform test -var-file=fixtures/offline.tfvars.example
```

PowerShell users should quote the last argument as `'-var-file=fixtures/offline.tfvars.example'`. Initialization downloads the signed provider from the registry. All seven test runs use the mocked AWS provider and plan commands with synthetic inputs. No AWS credentials, backend, or AWS service calls are required. These checks require internet access for uncached tool/provider/policy downloads; they are not an air-gapped workflow.

From the repository root, inspect all findings and then enforce the high/critical gate:

```text
trivy config --tf-vars infra/terraform/fixtures/offline.tfvars.example --exit-code 0 infra/terraform
trivy config --tf-vars infra/terraform/fixtures/offline.tfvars.example --severity HIGH,CRITICAL --exit-code 1 infra/terraform
```

Two resource-specific, expiring exceptions are documented in the ADR. The low-severity log-destination bucket finding remains visible. An expired exception is evaluated as a finding again.

## Input and state boundaries

- The fixture uses a nonexistent account, sample region/AZs, a synthetic certificate, and zero image digests. It is test data and cannot establish regional availability or deployable artifacts.
- A real account, region, certificate, supported RDS patch, image digests, unique final-snapshot identifier, and approved client CIDRs must be reviewed separately. No live values are selected here.
- Terraform creates only the application secret envelope. Passwords, DATABASE_URL, SECRET_KEY, and secret versions must remain outside Terraform configuration, variables, outputs, and state.
- Local state, saved plans, provider caches, variable files, and CLI credentials are ignored by Git. The committed lock and the nonsecret .example fixture are intentionally tracked.
- No remote state backend or cloud credentials are configured. Secure, encrypted, access-controlled remote state with locking must be established separately before live use.
- The existing API and frontend Dockerfiles run development servers. Production images must satisfy the task definition's non-root, read-only, port, health-check, and proxy contract before activation.
- Do not run live plan, apply, destroy, image publication, or AWS commands as part of this validation workflow.


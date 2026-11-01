# ADR 0003: Optional ECS foundation without provisioning

- **Status:** Accepted for local configuration and code review; live deployment is not authorized
- **Date:** 2026-11-01

## Scope

The finalized plan's fifth stage adds validated Terraform for the optional ECS Fargate path. This change defines infrastructure and tests it with a mocked AWS provider. It does not create resources, publish images, populate secrets, or add a deployment workflow. The local Compose application remains the demonstration path.

## Decisions

1. Pin Terraform 1.17.1 and AWS provider 6.71.0, with a committed provider lock for Linux and Windows. Initialization downloads tools; it does not require AWS credentials. Every Terraform test uses a mocked provider and a plan command.
2. Require an expected account, region, two AZs, existing certificate, verified RDS PostgreSQL 18 patch, production image digests, and a final-snapshot identifier. Synthetic fixture inputs are for validation only. There is no selected live account or region.
3. Default the deployment guard to false and ECS task count to zero. The guard is an accidental-use control, not an authorization system. Setting it true in a mocked test grants no permission for AWS work. Account restrictions provide a second check during a separately approved future deployment.
4. Use two AZs with edge, private application, and isolated database subnets. Only the edge route table reaches an internet gateway. Tasks have no public IP or general internet route. Private ECR, Logs, and Secrets Manager endpoints and a restricted S3 image-layer gateway replace NAT gateways.
5. Use an internet-facing ALB with HTTPS only, an existing ACM certificate, and an explicit IPv4 client allowlist. The default allows no clients; /24 or narrower inputs are required. No API or database port is exposed to clients. Public exposure still requires the separate deployment review.
6. Run the static frontend/reverse proxy and API in one Fargate task. The proxy serves the UI on 8080 and sends /api to the API on loopback port 8000. Both containers use UID 10001, read-only roots, dropped capabilities, and separate writable /tmp volumes. This is a shared task trust boundary. The existing development Dockerfiles do not satisfy this production image contract.
7. Separate the task execution role from the application task role. The application role has no attached AWS permissions. Execution permissions cover only the two image repositories, task logs, and the application secret/key. ECR authentication requires Resource "*"; it grants authentication rather than unrestricted repository reads. Task trust requires the expected account and an ECS source ARN.
8. Store no passwords or secret values in Terraform. RDS manages its administrator password in Secrets Manager. Terraform creates an empty application secret envelope; runtime DATABASE_URL and SECRET_KEY must be populated separately after approval. The application must use a dedicated restricted database user, not the RDS administrator.
9. Use private, encrypted Multi-AZ RDS with forced TLS, seven-day backups, deletion protection, final snapshots, and database logs. Use a rotating KMS key with a 30-day deletion window and prevent_destroy. The key must be retained while snapshots or logs encrypted with it are retained.
10. Enable task/VPC/database logs with 30-day CloudWatch retention, ALB access logs with bounded S3 retention, immutable encrypted ECR repositories, image scanning, health checks, and ECS deployment rollback. Alerts and operational response validation remain release work.

## Resource-specific scanner decisions

These two inline exceptions expire on **2026-11-30** and must also be reviewed before any deployment. They apply only to the named resources. Other high/critical IaC findings fail CI.

| Check and resource | Reason, impact, and compensating controls |
|---|---|
| AVD-AWS-0053, aws_lb.application | The optional design deliberately includes an external HTTPS edge. The database and tasks remain private; no clients are allowed by default, and configured clients must be explicitly restricted. This does not establish that application images or operations are ready for public use. |
| AVD-AWS-0132, aws_s3_bucket_server_side_encryption_configuration.access_logs | AWS ALB log delivery supports SSE-S3, so this bucket uses that encrypted-at-rest mode. Public access is blocked, ownership is enforced, transport is TLS-only, and version/retention controls apply. Application data, registry images, database storage, and CloudWatch logs use the customer-managed key. |

The low-severity AWS-0089 finding for server access logging on the ALB log bucket remains visible. This bucket is already a log destination; logging it to itself risks recursive log growth. Separate data-event monitoring can be considered during the operational review. Review this finding before deployment or by **2026-11-30**.

## Limitations and prerequisites

- Mocked plans validate configuration and security invariants. They do not prove AWS service availability, IAM runtime behavior, live TLS, end-to-end application operation, or teardown.
- ALB-to-frontend transport is HTTP inside the restricted VPC boundary; end-to-end TLS is not claimed. IPv6 and broad public access are excluded.
- Required follow-up: region/account/budget approval, current regional costs and quotas, supported RDS patch/AZs, certificate and DNS, secure remote state, least-privilege operator access, production images, restricted database identities and migrations, TLS certificate verification, secret rotation, trusted proxy/host handling, browser security headers, operational alerts, and a reviewed retention/teardown plan.
- A zero task count does not make a provisioned stack free: ALB, RDS, private endpoints, logs, keys, and storage can still incur charges. No costs or live cleanup behavior have been tested.

## References

- [Terraform mocked providers](https://developer.hashicorp.com/terraform/language/tests/mocking)
- [ECR private endpoint requirements](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)
- [Fargate networking](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-task-networking.html)
- [ALB log delivery and supported encryption](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/enable-access-logging.html)
- [AWS provider versioned source and documentation](https://github.com/hashicorp/terraform-provider-aws/tree/v6.71.0)

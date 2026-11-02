# Production image verification without deployment

The production Dockerfiles implement the reviewed serving contract, and a separate disposable Compose harness exercises them over HTTPS and database TLS. This workflow uses synthetic accounts/data and generates its own temporary credentials and certificates. It does not publish images, contact AWS services, or use live secrets.

Read [ADR 0004](decisions/0004-production-serving-and-local-tls.md) for proxy trust and the database grant model. Read the [deployment guide](deployment.md) for remaining live prerequisites.

## Reproduce on a Docker host

Use Docker Compose v2, Python 3.12, OpenSSL, and internet access for uncached image/package downloads. Docker is required for the image/runtime proof; the Python unit tests do not replace it. GitHub's PostgreSQL/Compose check is the reference automated run.

From the repository root in Bash on a disposable Docker host:

```bash
test_parent=$(mktemp -d)
python scripts/prepare_production_test.py --directory "$test_parent/tls"
set -a
. "$test_parent/tls/compose.env"
set +a
export COMPOSE_FILE=docker-compose.production-test.yml
export COMPOSE_PROJECT_NAME=tracker-production-local

docker compose config --quiet
docker compose build --pull db admin api frontend edge
docker compose up -d --wait --wait-timeout 90 db
docker compose run --rm -T --no-deps admin
docker compose up -d --wait --wait-timeout 180 api frontend edge
python scripts/production_smoke.py
```

Keep the generated directory outside the checkout. Do not display its environment file or private keys. The directory is private on the host; individual test server-key file mounts allow non-root containers to read the ephemeral key. The CA private key is never mounted. CI masks all generated credential values.

The setup-profile admin service is an explicit operation. Application startup does not run migrations or seed data. API readiness waits for the schema; a new database cannot serve workflows until initialization succeeds. No host database or API port is published. The local HTTPS fixture is bound only to 127.0.0.1:8443.

The production smoke also performs the existing authenticated HTTP workflow checks with Secure cookies and same-origin referers. Existing frontend component tests continue to check rendering; this is not a browser automation test or a live AWS test.

## Runtime and TLS contracts

- Gunicorn binds 127.0.0.1:8000 in the shared task network. Nginx listens on 8080 and proxies /api over task loopback.
- Set APP_HOST consistently in both containers to the reviewed certificate/DNS hostname. Forwarded Host/port/prefix are not trusted. Do not expose the frontend outside the reviewed ALB/security-group path or change proxy counts without tests.
- The local edge appends a client hop and sets HTTPS as ALB does. The frontend appends the edge hop. The application uses the second tail client address rather than a caller-supplied leading address.
- Supply a runtime DATABASE_URL with sslmode=verify-full and an absolute CA path. The image provides /etc/tracker/rds-ca.pem; the fixture mounts a test CA at /etc/tracker/test-ca.pem. Never copy the ephemeral test CA or key into a deployment image.
- Local database credentials are generated independently for administration and runtime. The runtime identity cannot modify user roles, rewrite/delete audit events, delete notes, or own/create schema objects.
- Production image containers use UID/GID 10001, read-only roots, dropped capabilities, temporary writable storage, and no-new-privileges in Compose. Health checks and worker temporary files use the same constrained runtime.
- No image self-starts a migration, creates a user, embeds credentials, or prints secrets.

## Checks and cleanup

Useful non-container checks from the repository root:

```text
python scripts/validate_contract.py
python scripts/validate_production_assets.py
python -m pip_audit --strict --disable-pip --no-deps -r backend/requirements-production.lock
```

The production lock is resolved from the backend production extra under existing dependency constraints. Runtime installs use the complete lock and a local package wheel, followed by pip check. Do not independently loosen the lock when updating the extra. Verify a clean Linux image install and audit together; Gunicorn execution is a Linux/container check.

After testing, remove only this disposable stack and its named database:

```bash
docker compose --profile setup down --volumes --remove-orphans
```

This deletes the synthetic test database. Remove the generated certificate/credential directory through your normal local file cleanup after confirming it is the disposable path. CI tears down the containers/volume and discards its hosted runner. No live-data or AWS cleanup is performed.

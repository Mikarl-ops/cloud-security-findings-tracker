# Cloud Security Findings Tracker

A small portfolio application for reviewing synthetic cloud security findings. It connects a React and TypeScript dashboard to a Flask API and PostgreSQL, with session authentication, analyst and viewer roles, investigation notes, and an audit history.

The Flask API, PostgreSQL schema and migrations, sessions, analyst/viewer workflows, React dashboard, and local Compose environment are implemented. Pull requests now run automated tests, integration checks, code analysis, dependency audits, secret scanning, and scans of all three container images. Deployment remains future work.

The project uses synthetic sample data only. It does not ingest real telemetry, perform automated containment, or require AWS. The optional AWS target is ECS Fargate; no AWS resources are created by this repository foundation.

## Design documents

- [Architecture](docs/architecture.md)
- [Threat model](docs/threat-model.md)
- [API contract](docs/api-contract.md)
- [OpenAPI 3.1 specification](docs/openapi.json)
- [Data model](docs/data-model.md)
- [Architecture decision record](docs/decisions/0001-architecture.md)
- [Backend and session storage decisions](docs/decisions/0002-backend-data-and-session-storage.md)
- [Development conventions](docs/development.md)
- [CI checks, security gates, and maintenance](docs/ci-security.md)

## Planned repository structure

```text
backend/                 Flask API package, models, migrations, and tests
database/                Synthetic seed data and derived PostgreSQL image
docs/                    Architecture, API, threat model, and decisions
frontend/                React + TypeScript + Vite application
infra/terraform/         Reserved for the optional later AWS milestone
scripts/                 Local validation helpers
docker-compose.yml       Local PostgreSQL, API, and frontend services
```

The API includes health checks, session login/logout, role-protected finding reads and analyst writes, bounded filtering and pagination, note creation, and audit history. Only synthetic findings belong in this project. Terraform and deployment remain later work.

## Local prerequisites

- Python 3.12
- Node.js 24 LTS and npm
- Docker Engine with Docker Compose v2 for the local development stack
- Git

The design baseline is Python 3.12.14, Node.js 24 LTS, and PostgreSQL 18.6. Use the current security patch in each supported release line. Runtime choices were checked against the official release and support pages on 2026-10-28.

## Start the local application

1. Copy `.env.example` to `.env`. Set `POSTGRES_PASSWORD` to a random hex value and `SECRET_KEY` to a separate random value. For each value, run `python -c "import secrets; print(secrets.token_hex(32))"` and copy the output into `.env`. These values are local only.
2. Build and start PostgreSQL, the API, and the dashboard with `docker compose up --build`.
3. Create the first local analyst account: `docker compose exec api flask --app tracker:create_app create-user analyst --role analyst`. The password is entered interactively and is not echoed.
4. Open <http://localhost:5173> and sign in. The API is also reachable at <http://localhost:5000> for local checks.
5. Stop the services with `docker compose down`. To also remove the local database volume and its data, use `docker compose down --volumes`.

The API container applies database migrations and loads the documented synthetic findings on startup. The seed command is idempotent and does not remove or rewrite existing findings. For a non-container backend workflow, see [backend setup](backend/README.md).

The Vite development server proxies `/api` requests to the API, so the browser uses same-origin session cookies and CSRF protection during local development.

## Automated checks

The [quality workflow](.github/workflows/ci.yml) tests both applications and starts a disposable PostgreSQL/Compose stack. The [security workflow](.github/workflows/security.yml) runs Bandit, pip-audit, npm audit, Gitleaks, and Trivy. Actions use pinned commits and read-only repository access. The active `Protect main` ruleset requires a pull request and all eleven checks before merging. See the [check policy](docs/ci-security.md) for local commands, failure thresholds, the reviewed minimatch security override, exceptions, and enforced merge settings.

## Safety and data handling

Never commit `.env`, passwords, session secrets, real findings, or production telemetry. The tracked `.env.example` contains placeholders only. The local stack creates no AWS resources and does not deploy the application.

## Project schedule

1. Design and foundation — merged
2. Flask API, PostgreSQL migrations, findings, notes, audit, sessions, and authorization — merged
3. Dashboard and local Docker Compose workflow — merged and exercised in CI
4. Pull-request CI, tests, and security checks — implemented
5. Terraform and optional ECS Fargate deployment
6. Security scenarios, documentation, and portfolio walkthrough


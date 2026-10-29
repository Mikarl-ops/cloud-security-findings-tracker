# Cloud Security Findings Tracker

A small portfolio application for reviewing synthetic cloud security findings. It connects a React and TypeScript dashboard to a Flask API and PostgreSQL, with session authentication, analyst and viewer roles, investigation notes, and an audit history.

**Milestone 1 is merged.** Milestone 2 adds the Flask API, PostgreSQL schema and migrations, server-managed sessions, role checks, finding status changes, investigation notes, and audit history. The React workflows and complete API-plus-database Compose environment remain later work.

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

## Planned repository structure

```text
backend/                 Flask API package, models, migrations, and tests
database/seed/           Synthetic sample-data conventions
docs/                    Architecture, API, threat model, and decisions
frontend/                React + TypeScript + Vite application
infra/terraform/         Reserved for the optional later AWS milestone
scripts/                 Local validation helpers
docker-compose.yml       Local PostgreSQL service
```

The API includes the liveness and readiness checks, session login/logout, role-protected finding reads and analyst writes, bounded filtering and pagination, note creation, and audit history. Only synthetic findings belong in this project. CI security checks, Terraform, and deployment instructions remain later milestones.

## Local prerequisites

- Python 3.12
- Node.js 24 LTS and npm
- Docker Engine with Docker Compose v2 for the local PostgreSQL service
- Git

The design baseline is Python 3.12.14, Node.js 24 LTS, and PostgreSQL 18.6. Use the current security patch in each supported release line. Runtime choices were checked against the official release and support pages on 2026-10-28.

## Start the local API

1. Copy `.env.example` to `.env`. Replace the database password and secret key with random local-only values; keep the password in `POSTGRES_PASSWORD` and `DATABASE_URL` consistent.
2. Start PostgreSQL: `docker compose up -d db`.
3. In `backend/`, create and activate a Python virtual environment, install the pinned dependencies with `python -m pip install -r requirements.lock`, then install the local package with `python -m pip install --no-deps --no-build-isolation -e .`.
4. Apply the reviewed schema migrations with `python -m flask --app tracker:create_app db upgrade`.
5. Create a local analyst account with `python -m flask --app tracker:create_app create-user analyst --role analyst`. The password is entered interactively and is not echoed.
6. Run backend checks with `python -m pytest` and `ruff check .`.
7. In `frontend/`, run `npm ci`, then `npm run dev` or `npm test`.

To run the API, activate the backend virtual environment and run `flask --app tracker:create_app run --host 127.0.0.1` from `backend/`. The API requires the local database migration and environment values above. The frontend remains a placeholder until Milestone 3.

## Safety and data handling

Never commit `.env`, passwords, session secrets, real findings, or production telemetry. The tracked `.env.example` contains placeholders only. Do not run Terraform apply, create AWS resources, or deploy the application as part of Milestone 2.

## Project schedule

1. Design and foundation — merged
2. Flask API, PostgreSQL migrations, findings, notes, audit, sessions, and authorization — implemented locally
3. Dashboard and complete local Docker Compose workflow
4. Pull-request CI, tests, and security checks
5. Terraform and optional ECS Fargate deployment
6. Security scenarios, documentation, and portfolio walkthrough


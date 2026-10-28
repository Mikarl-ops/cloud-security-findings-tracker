# Cloud Security Findings Tracker

A small portfolio application for reviewing synthetic cloud security findings. It connects a React and TypeScript dashboard to a Flask API and PostgreSQL, with session authentication, analyst and viewer roles, investigation notes, and an audit history.

**Milestone 1 status:** architecture, API, data model, threat model, development conventions, and the local project foundation are being established. Finding workflows and database-backed behavior are not implemented yet.

The project uses synthetic sample data only. It does not ingest real telemetry, perform automated containment, or require AWS. The optional AWS target is ECS Fargate; no AWS resources are created by this repository foundation.

## Design documents

- [Architecture](docs/architecture.md)
- [Threat model](docs/threat-model.md)
- [API contract](docs/api-contract.md)
- [OpenAPI 3.1 specification](docs/openapi.json)
- [Data model](docs/data-model.md)
- [Architecture decision record](docs/decisions/0001-architecture.md)
- [Development conventions](docs/development.md)

## Planned repository structure

```text
backend/                 Flask API package and tests
database/seed/           Synthetic sample-data conventions
docs/                    Architecture, API, threat model, and decisions
frontend/                React + TypeScript + Vite application
infra/terraform/         Reserved for the optional later AWS milestone
scripts/                 Local validation helpers
docker-compose.yml       Local PostgreSQL service
```

The current code is only a runnable health-check/API shell and a placeholder frontend. Database migrations, authentication behavior, findings CRUD, CI security checks, Terraform, and deployment instructions will be added in later milestones.

## Local prerequisites

- Python 3.12
- Node.js 24 LTS and npm
- Docker Engine with Docker Compose v2 for the local PostgreSQL service
- Git

The design baseline is Python 3.12.14, Node.js 24 LTS, and PostgreSQL 18.6. Use the current security patch in each supported release line. Runtime choices were checked against the official release and support pages on 2026-10-28.

## Start the local foundation

1. Copy `.env.example` to `.env`, then replace the local database password with a value used only on this machine.
2. Start PostgreSQL: `docker compose up -d db`.
3. In `backend/`, create and activate a Python virtual environment, install the pinned dependencies with `python -m pip install -r requirements.lock`, then install the local package with `python -m pip install --no-deps --no-build-isolation -e .`.
4. Run backend checks with `python -m pytest`.
5. In `frontend/`, run `npm ci`, then `npm run dev` or `npm test`.

To run the API shell, activate the backend virtual environment and run `flask --app tracker:create_app run --host 127.0.0.1` from `backend/`. In a separate terminal, run `npm run dev` from `frontend/`; Vite proxies `/api` to the Flask server. The Milestone 1 shell does not connect to PostgreSQL yet. Its only API operation is the unauthenticated liveness check; the database schema and remaining contract operations are design artifacts, not working features yet.

## Safety and data handling

Never commit `.env`, passwords, session secrets, real findings, or production telemetry. The tracked `.env.example` contains placeholders only. Do not run Terraform apply, create AWS resources, or deploy the application as part of Milestone 1.

## Project schedule

1. Design and foundation — current milestone
2. Flask API, PostgreSQL migrations, findings, notes, audit, and sessions
3. Dashboard and complete local Docker Compose workflow
4. Pull-request CI, tests, and security checks
5. Terraform and optional ECS Fargate deployment
6. Security scenarios, documentation, and portfolio walkthrough


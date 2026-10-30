# Development conventions

## Scope discipline

The six milestones are:

1. Design and foundation
2. Flask API, database migrations, findings, notes, sessions, and authorization
3. React workflows and complete local Compose environment
4. Pull-request CI, quality checks, and security scanning
5. Terraform and the optional ECS Fargate path
6. Security scenarios, final documentation, and walkthrough

Do not add feature code for a later milestone without updating the scope and decision record. AWS commands and provisioning are not part of local setup.

## Branches and pull requests

- Use short-lived branches named docs/topic, feat/topic, fix/topic, or chore/topic.
- Submit changes through a pull request to main; do not commit directly to main.
- Keep each pull request focused. Describe behavior, tests run, security impact, and follow-up work.
- Do not merge a pull request without the owner's approval.

## Code conventions

- Python: type hints for public functions, small Flask blueprints, application factory, SQLAlchemy models, UTC-aware datetimes, pytest, and Ruff formatting/linting.
- TypeScript: strict mode, functional React components, explicit API types, Vitest, and React Testing Library.
- Database: schema changes only through reviewed Alembic migrations; use constraints and indexes for invariants and query paths.
- API: validate every request server-side; use stable status codes and RFC 9457 errors; keep request and response schemas documented.
- Security: role checks belong in API services/routes; render finding and note text as text; never store authentication tokens in browser storage.
- Test data: use synthetic fixtures only. Make tests deterministic and avoid calls to AWS or public services.

## Local configuration and secrets

- Copy .env.example to .env; .env is ignored by Git.
- Use distinct local-only credentials. Never put passwords, API tokens, secret keys, real telemetry, or personal data in tracked files.
- Production secret management and AWS identity are not configured by the local development stack.
- Do not paste secrets into issue or pull-request descriptions, test output, or logs.

## Quality checks

Before a pull request, run the checks relevant to changed files:

- Backend: python -m pytest and ruff check .
- Frontend: npm test, npm run typecheck, npm run lint, and npm run build.
- Data and docs: run python scripts/validate_contract.py and inspect Markdown links.
- Infrastructure: later milestone only; terraform fmt -check, terraform validate, and IaC scanning must not require AWS credentials.

The initial CI workflow is deferred to Milestone 4. Local validation commands are documented now so the workflow can mirror them later.

## Documentation and review

Keep architecture, API, data model, and threat model in sync when a contract changes. Every accepted security exception needs its reason, impact, and review date. Clearly distinguish implemented behavior from planned behavior.


# ADR 0002: backend data and session storage

**Status:** Accepted

**Date:** 2026-10-29

## Context

Milestone 2 adds persistent finding workflows and server-managed authentication while keeping local development independent of AWS. Schema changes must be reviewable migrations, status updates must not overwrite concurrent work, and audit records must commit with the action they describe.

## Decisions

- Use PostgreSQL with UUID identifiers, constrained status and role values, JSONB for structured allowlisted metadata, and Alembic migrations through Flask-Migrate.
- Increment a finding version on every status update and require `expected_version` from clients. Write status changes and audit events in the same transaction.
- Keep notes append-only through the API. Store only a note ID in a note-added audit event.
- Reuse Flask-Session's server-side session lifecycle, but provide an application SQLAlchemy adapter whose table is created only by Alembic migrations. Store a SHA-256 hash of the opaque cookie ID, serialize session values as strict JSON, and never use a pickle fallback. See the [Flask-Session 0.8 session interface](https://github.com/pallets-eco/flask-session/blob/0.8.0/src/flask_session/base.py) and its [default SQLAlchemy adapter](https://github.com/pallets-eco/flask-session/blob/0.8.0/src/flask_session/sqlalchemy/sqlalchemy.py).
- Rotate the session ID at login, invalidate it at logout, and enforce a 30-minute sliding idle lifetime capped by an eight-hour absolute lifetime. Require CSRF tokens for unsafe cookie-authenticated requests.
- Throttle failed logins to ten per fifteen minutes for the HMAC of the normalized username and server-observed client address. Store neither raw value in the throttle table.
- Create local accounts only through an interactive CLI command. Hash passwords with Argon2id; do not accept password values on the command line or commit credentials.

## Consequences

- Local API tests can use SQLite and synthetic records; the migration is also compiled to PostgreSQL SQL without opening a network connection.
- A deployment behind a reverse proxy must define trusted-proxy handling and verify the client address used by login throttling. Edge-level rate limiting remains a later deployment concern.
- The runtime database identity should be restricted so audit events cannot be updated or deleted. That privilege boundary is outside local Milestone 2 and must be configured before deployment.
- No finding ingestion route, real telemetry, frontend workflow, CI pipeline, Terraform, AWS resource, or live deployment is introduced by this decision.

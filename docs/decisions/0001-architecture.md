# ADR 0001: Application architecture and security baseline

- **Status:** Accepted for Milestone 1
- **Date:** 2026-10-28

## Context

The portfolio needs one focused application that connects cloud security investigation to application delivery practices. The complete project must work locally without AWS credentials. The existing portfolio already contains a CloudTrail response lab, a detection-engineering lab, and synthetic DFIR case files; the new project should add an analyst workflow and persistent application rather than duplicate those exercises.

## Decisions

1. **Application shape:** one React + TypeScript frontend, one Flask REST API, and one PostgreSQL database. Do not split the application into microservices.
2. **Local environment:** Docker Compose runs PostgreSQL locally. Tests and API development must not call AWS.
3. **Authentication:** server-managed sessions stored in PostgreSQL with an opaque browser cookie. Do not use client-side JWTs or browser local storage for session tokens.
4. **Authorization:** two server-enforced roles: analyst and viewer. Do not rely on disabled UI controls for security.
5. **CSRF:** Flask-WTF global CSRF protection with a token sent in X-CSRFToken for unsafe requests; SameSite=Lax is defense in depth.
6. **Password storage:** Argon2id hashes; no committed or hard-coded demo password.
7. **Findings:** synthetic data only, bounded fields, status workflow, plain-text notes, and append-only audit history.
8. **API:** versioned under /api/v1, JSON requests/responses, RFC 9457 problem details, bounded pagination and request sizes.
9. **Optional cloud target:** ECS Fargate may be considered in Week 5. RDS, networking, IAM, costs, and teardown are a later design gate. This ADR authorizes no AWS provisioning.
10. **Runtime baseline:** Python 3.12, Node.js 24 LTS, PostgreSQL 18.6. Keep dependency lockfiles current and apply security patches within supported release lines.
11. **Testing:** pytest for backend behavior; Vitest and React Testing Library for frontend components. Keep tests deterministic and synthetic.
12. **Migrations and CI:** use Alembic through Flask-Migrate when the data model is implemented. CI and security scanning are planned for Milestone 4, not part of this initial shell.

## Consequences

- The first milestone can settle API, schema, trust boundaries, and local development without implementing findings behavior.
- PostgreSQL stores both application data and server-side sessions. Expired SQL-backed sessions require cleanup.
- Same-origin deployment avoids broad CORS configuration; Vite proxies the local API.
- Public deployment, production identity, rate-limit infrastructure, backups, and retention remain future prerequisites.

## Reconsider this ADR if

- the project becomes multi-tenant;
- an external identity provider or MFA becomes a requirement;
- session storage or database scaling requires a separate service;
- the project begins processing real cloud telemetry;
- the optional AWS design changes materially.


# Architecture

## Purpose and scope

The Cloud Security Findings Tracker is a compact, single-application portfolio project. It presents synthetic cloud-security findings, supports analyst investigation and status updates, and records a history of those actions. It is not a SIEM, alert detector, multi-tenant service, or automated response system.

The local application must be testable without an AWS account. AWS is an optional later deployment target and remains outside this milestone.

## Components

```mermaid
flowchart LR
    Browser[Analyst or viewer browser] -->|same-origin HTTPS in deployment| UI[React + TypeScript]
    UI -->|JSON API, cookie session, CSRF token| API[Flask REST API]
    API --> AUTH[Server-side session and role checks]
    AUTH --> DB[(PostgreSQL)]
    API --> FIND[Findings and notes]
    API --> AUDIT[Append-only audit events]
    SEED[Synthetic seed data] --> DB

    DEV[Developer] --> REPO[GitHub repository]
    REPO --> CI[GitHub Actions, later milestone]
    CI -. later .-> IMAGE[Container image]
    IMAGE -. optional .-> ECS[ECS Fargate]
    ECS -. optional .-> RDS[(Managed PostgreSQL)]
```

The planned ECS path is not part of the local runtime, and no AWS infrastructure is included in this foundation.

## Trust boundaries

1. **Browser to application:** the browser is untrusted. The API validates every field, authenticates every protected request, checks the user's role on every action, and applies CSRF protection to cookie-authenticated state changes.
2. **Application to PostgreSQL:** the API uses a least-privilege database identity. Queries are parameterized through SQLAlchemy. The database stores passwords only as Argon2id hashes and stores server-side session state separately from browser cookies.
3. **Developer and dependency supply chain:** repository changes are reviewed through pull requests. The later CI milestone will add tests, code analysis, dependency auditing, secret scanning, and infrastructure checks.
4. **Optional AWS boundary:** only a later, separately reviewed milestone may add cloud resources. Local tests and CI do not need AWS credentials.

## Request flow

- The browser loads the React single-page application. Vite proxies /api during local development; a later deployment will serve the frontend and API from one origin.
- The browser obtains an anti-CSRF token and sends it in the X-CSRFToken header for state-changing requests.
- Flask resolves the opaque session cookie against server-side session storage. The current user and role are loaded from the user record rather than trusted from browser-provided fields.
- Authorization and input validation run before business operations.
- A finding update or note creation and its audit event are committed in one database transaction.
- API errors use stable RFC 9457 problem details and do not reveal stack traces, credentials, or SQL information.

## Availability checks

- GET /api/v1/health/live reports that the process is running. It performs no dependency checks and returns no environment or secret details.
- GET /api/v1/health/ready is planned for the database milestone. It returns success only when the database is reachable and the schema is usable; otherwise it returns a generic service-unavailable response.

## Runtime baseline

As checked on 2026-10-28, the development baseline is Python 3.12.14, Node.js 24 LTS, and PostgreSQL 18.6. These versions are recorded so the local skeleton is repeatable; update to current security patches within each supported major/minor line. The PostgreSQL project supports each major release for five years.

## Explicit exclusions

- Real cloud or identity-provider event ingestion
- Automated blocking, account changes, or incident response
- User self-registration and multi-tenancy
- SSO, MFA, and external identity federation
- Public internet exposure before the deployment threat review
- AWS resources, live deployment, or cloud credentials in local setup

## References

- [Node.js release schedule](https://nodejs.org/en/about/previous-releases)
- [Python version support](https://devguide.python.org/versions/)
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [Flask configuration](https://flask.palletsprojects.com/en/stable/config/)


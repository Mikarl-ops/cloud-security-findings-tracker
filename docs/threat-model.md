# Threat model

**Status:** Local API/session controls, plain-text UI rendering, automated quality/security checks, and non-root container execution are implemented. Deployment controls and AWS remain later work. Thresholds and remaining findings are recorded in the [CI policy](ci-security.md).

## Scope

This model covers the local React + TypeScript frontend, Flask REST API, PostgreSQL database, server-managed sessions, synthetic data, and PR validation pipeline. The optional AWS architecture is not provisioned. The model must be revisited before any public deployment or real telemetry is introduced.

## Assets

- Finding titles, summaries, status, notes, and audit history
- User identifiers, password hashes, and account roles
- Session identifiers and server-side session data
- Database and application configuration, including secret keys
- Availability and integrity of the local application
- Correct labeling of synthetic records as synthetic

## Actors and trust assumptions

| Actor | Capability or assumption |
|---|---|
| Unauthenticated visitor | Can send arbitrary HTTP requests and attempt login abuse |
| Read-only viewer | Can read permitted findings and history but must not change state |
| Analyst | Can change finding status and add notes through authorized routes |
| Developer | Can change source, dependencies, configuration, and sample data |
| Dependency or build service | May be compromised; pinned actions, verified scanner archives, audits, and image scans reduce but do not remove this risk |
| Local database operator | Can inspect local data; local data must remain synthetic |

The browser, request parameters, finding text, notes, and session cookie are untrusted. A successful login does not imply permission to perform every action.

## Data-flow boundaries

- Browser to frontend/API: untrusted network input; HTTPS is required when deployed.
- Flask process to PostgreSQL: authenticated service connection; use a dedicated runtime identity with only required privileges.
- Git repository to build pipeline: changes are untrusted until reviewed and validated.
- Optional AWS deployment: a separate trust boundary that requires cost, IAM, secret, network, and teardown review.

## Threats and required controls

| Threat | Impact | Required controls | Validation evidence |
|---|---|---|---|
| Credential guessing or account enumeration | Account takeover or disclosure that an account exists | Argon2id password hashing; generic login failures; HMAC-keyed throttling with status 429; no public self-registration; do not log passwords | Authentication tests cover wrong password, inactive account, throttling, and generic response |
| Session fixation, theft, or replay | Unauthorized use of an analyst session | Rotate session ID after login and privilege change; server-side session store; 30-minute idle and eight-hour absolute lifetime; invalidate on logout; HttpOnly, Secure in HTTPS, SameSite=Lax, host-only cookie; never expose session IDs in logs | Session tests and cookie-attribute checks |
| Cross-site request forgery | Victim's browser submits an unwanted state change | Flask-WTF CSRF protection for every unsafe cookie-authenticated request; send token in X-CSRFToken; check Origin where present; SameSite is defense in depth | Missing, invalid, and valid token tests for login, logout, status, and note operations |
| Broken object or function authorization | Viewer changes a finding or accesses an unpermitted record | Enforce analyst/viewer authorization in Flask on every endpoint and object; never rely on React controls | Direct API tests for viewer writes, missing session, and each role |
| Stored cross-site scripting through finding or note text | Script runs in another user's browser | Treat stored text as untrusted; render as text; avoid dangerouslySetInnerHTML; restrict response content types; add a suitable Content Security Policy when serving the UI | Frontend tests with HTML-like text; header check in deployment milestone |
| SQL injection or malformed input | Data exposure, modification, or service failure | Use SQLAlchemy parameterized queries; validate type, length, enum, time ranges, pagination, and JSON size; reject unsupported content types and oversized bodies | API validation and database integration tests |
| Resource exhaustion | Slow queries, large responses, or login flood | Bounded page size (maximum 100), bounded request body (16 KiB), bounded note length (4,000 characters), database timeouts, login throttling, and rate limits at the edge if public | Limit-boundary tests and load limits reviewed before deployment |
| Audit history tampering or misleading records | Loss of investigation accountability | Write finding changes and audit events in one transaction; do not expose update/delete routes for audit events; runtime database role receives read/insert only for audit records; record actor, time, event type, finding ID, and safe changed fields | Tests verify rollback on audit failure and reject audit mutation |
| Secret or sensitive telemetry leakage | Account compromise or privacy harm | .env is ignored; no secret defaults; full-history Gitleaks scan with redacted output; only synthetic records are accepted; do not log credentials, session IDs, note bodies, or raw request bodies | CI secret scan and tracked-file validation; detailed logging review remains release work |
| Misleading synthetic alert presented as real | Incorrect security conclusions | Label the environment and sample records synthetic; document data provenance and limitations; no claims of production detection | README and sample-data review |

## Data-handling rules

- Seed data must be fabricated and clearly labeled synthetic. Never copy real CloudTrail, GuardDuty, identity, or incident records.
- Findings and notes are plain text; no HTML or Markdown rendering is accepted in the first version.
- Logs may include request ID, actor ID, operation, object ID, status code, and duration. Do not log passwords, cookies, session tokens, note contents, database URLs, or secret values.
- Errors exposed to clients are generic and structured; stack traces and SQL messages stay in server logs.
- A retention period for findings, notes, audit events, and session rows must be agreed before any real deployment.

## Residual risks and follow-up

- A compromised analyst account can perform analyst actions; MFA and identity federation are out of scope for the local MVP.
- The application has no independent security boundary between two customer organizations; multi-tenancy is explicitly excluded.
- A local single-node database is not a production backup or availability strategy.
- Login throttling uses the server-observed remote address; any reverse-proxy deployment must define and test trusted-proxy handling before relying on the address in rate-limit keys.
- Automated scans cover known advisories and specific code patterns, not all vulnerabilities. The temporary minimatch compatibility override and the development-bind exception require the dated follow-ups in the [CI policy](ci-security.md). Optional AWS IAM/network design, production container review, and operational alerting remain later work.
- No application in this milestone is suitable for public exposure. Public deployment requires the complete authentication, authorization, CSRF, TLS, logging, rate-limit, secret, and operational controls to be implemented and reviewed.

## References

- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
- [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x00-header/)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)


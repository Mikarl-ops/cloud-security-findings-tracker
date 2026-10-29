# API contract

**Base path:** /api/v1  
**Media type:** application/json; charset=utf-8  
**Errors:** application/problem+json following [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html).

This is the agreed v1 contract. Milestone 2 implements the health, authentication, findings, notes, and history routes. The React client and CI pipeline remain later milestones.

## Authentication and roles

Authentication uses an opaque `csft_session` cookie backed by server-side session storage. The API does not accept bearer tokens or credentials in URLs. The cookie is HttpOnly, host-only, and SameSite=Lax; it is Secure in HTTPS deployments. State-changing requests require a CSRF token in the `X-CSRFToken` header.

Roles:

- analyst: read findings/history, change status, and add notes.
- viewer: read findings/history only.

All protected routes check authentication and authorization server-side. The role is loaded from the current user record, not trusted from request data.

## Endpoints

| Method and path | Access | Purpose |
|---|---|---|
| GET /health/live | Public | Liveness only; no dependency or secret details |
| GET /health/ready | Public | Planned database readiness check; returns 503 when the service cannot serve data |
| GET /auth/csrf | Public | Establishes an anonymous session and returns `{ "csrf_token": "<token>" }`; Cache-Control: no-store |
| POST /auth/login | Public + CSRF | Authenticates a local user, rotates the session ID, and returns the user summary |
| GET /auth/session | Authenticated | Returns the current user's ID, username, and role |
| POST /auth/logout | Authenticated + CSRF | Invalidates the server-side session and expires the cookie; returns 204 |
| GET /findings/summary | Viewer or analyst | Counts by status and severity |
| GET /findings | Viewer or analyst | Bounded, filtered, paginated finding list |
| GET /findings/{findingId} | Viewer or analyst | Finding details |
| PATCH /findings/{findingId} | Analyst + CSRF | Changes status with optimistic concurrency |
| GET /findings/{findingId}/notes | Viewer or analyst | Paged notes in creation order |
| POST /findings/{findingId}/notes | Analyst + CSRF | Adds one immutable note |
| GET /findings/{findingId}/history | Viewer or analyst | Paged audit events in chronological order |

There are no finding, note, or audit delete endpoints. User self-registration and arbitrary event ingestion are out of scope.

## Request and response shapes

### Login

POST /auth/login

```json
{
  "username": "analyst",
  "password": "provided-out-of-band"
}
```

A successful response is 200 and sets the session cookie:

```json
{
  "user": {
    "id": "5b9a2294-0c55-4cf1-9e9a-141ca2b8669a",
    "username": "analyst",
    "role": "analyst"
  }
}
```

Invalid credentials and inactive accounts return the same generic 401 problem. After ten failures for a normalized username and observed client address within fifteen minutes, further attempts return 429 with Retry-After. The example password is explanatory text, not a usable account.

### List findings

GET /findings?status=new&severity=high&page=1&page_size=25

- Filters: status, severity, source, observed_from, observed_to.
- page defaults to 1 and must be positive.
- page_size defaults to 25 and is limited to 100.
- Sort order is observed_at DESC, id DESC.
- Unknown filters, invalid enum values, invalid dates, and reversed date ranges return 400.

```json
{
  "items": [
    {
      "id": "9beadf7a-11fb-47b0-a134-22b06a0e8bbc",
      "title": "Repeated failed console sign-ins",
      "source": "cloudtrail",
      "severity": "medium",
      "status": "new",
      "observed_at": "2026-01-14T08:30:00Z",
      "updated_at": "2026-01-14T08:30:00Z",
      "version": 1
    }
  ],
  "page": 1,
  "page_size": 25,
  "total": 1,
  "pages": 1
}
```

List responses omit raw provider payloads. Metadata exposed in detail responses is restricted to documented, allowlisted fields.

### Findings summary

GET /findings/summary returns `total`, `by_status`, and `by_severity`. Both count objects contain every supported status or severity key, including keys whose count is zero.

### Finding detail

GET /findings/{findingId} returns:

```json
{
  "id": "9beadf7a-11fb-47b0-a134-22b06a0e8bbc",
  "title": "Repeated failed console sign-ins",
  "description": "Synthetic example for analyst triage.",
  "source": "cloudtrail",
  "source_event_id": "synthetic-event-001",
  "severity": "medium",
  "status": "new",
  "observed_at": "2026-01-14T08:30:00Z",
  "evidence_summary": "Several failed sign-ins in a short window.",
  "metadata": {
    "region": "ap-southeast-1"
  },
  "resolution_reason": null,
  "created_at": "2026-01-14T08:31:00Z",
  "updated_at": "2026-01-14T08:31:00Z",
  "version": 1
}
```

### Status change

PATCH /findings/{findingId}

```json
{
  "status": "investigating",
  "expected_version": 1,
  "resolution_reason": null
}
```

expected_version is required. resolution_reason is required when entering resolved or dismissed and is limited to 1,000 characters. The response is 200 with the updated finding. A stale version returns 409. An unsupported transition or missing resolution reason returns 422.

Allowed transitions:

- new -> investigating or dismissed
- investigating -> resolved or dismissed
- resolved -> investigating
- dismissed -> investigating

Every successful change creates an audit event in the same database transaction.

### Add note

POST /findings/{findingId}/notes

```json
{
  "body": "Synthetic triage note: review adjacent identity activity."
}
```

body is plain text from 1 to 4,000 characters. Success returns 201 and the new note. Notes cannot be edited or deleted in v1. A note-added audit event records the note ID but does not duplicate the note body.

### Pagination for notes and history

Both endpoints accept page and page_size with the same defaults and limits as findings. Note bodies and audit event details are not included in findings-list responses.

Notes are returned oldest first with their author username and plain-text body. History is returned oldest first with the actor username, event type, timestamp, safe event details, and request ID. A note-added event contains only the note ID, not its body.

### Health

GET /health/live returns 200 with {"status":"ok"} when the process is running.

GET /health/ready returns 200 with {"status":"ready"} only when PostgreSQL and the required schema are available. Otherwise it returns 503 with a generic error. It does not report hostnames, schema names, or credentials.

## Error format

```json
{
  "type": "about:blank",
  "title": "Validation failed",
  "status": 422,
  "detail": "One or more fields are invalid.",
  "instance": "/api/v1/findings/9beadf7a-11fb-47b0-a134-22b06a0e8bbc",
  "request_id": "c71f7e74-9d29-4b7e-a8d5-239a70a68482"
}
```

detail helps the client correct the request but never contains stack traces, SQL, secrets, or internal file paths. Field validation may include a bounded errors array of field and code entries.

| Status | Use |
|---|---|
| 400 | Malformed JSON, invalid query parameters, or unsupported filter |
| 401 | Missing or invalid authentication |
| 403 | Authenticated user lacks the required role, or CSRF validation failed |
| 404 | Resource does not exist |
| 409 | Stale expected_version |
| 413 | Request body exceeds 16 KiB |
| 415 | Unsupported request content type |
| 422 | Valid JSON with invalid fields or state transition |
| 429 | Login or request rate limit reached |
| 500 | Unexpected error; generic client response |

## Input and transport limits

- JSON requests only; reject unsupported content types.
- Maximum request body: 16 KiB.
- Maximum page_size: 100.
- Maximum note body: 4,000 characters.
- Maximum resolution reason: 1,000 characters.
- All timestamps use RFC 3339 UTC values.
- Deployed API traffic must use HTTPS. CORS is disabled for the same-origin design; local development uses the Vite proxy.


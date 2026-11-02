# ADR 0004: Production serving images and local TLS verification

- **Status:** Implemented for local validation and code review; publication and deployment are not authorized
- **Date:** 2026-11-02

## Scope

Continue the optional ECS preparation by implementing the image contract from ADR 0003. Keep the default development Dockerfiles and Compose workflow available. Provide separate production-serving images and prove their behavior in a disposable local/CI environment. No live cloud plan, resource, secret value, registry publication, or deployment workflow is introduced.

## Serving and trust decisions

- The API uses Gunicorn 26.2.0 with two synchronous workers, a loopback bind on 8000, bounded worker lifetime/timeouts, and secure temporary-file APIs. It runs as UID/GID 10001. Production dependencies are fully version-pinned separately from the development lock; wheels and the package are installed before pip/build tools are removed from the runtime image.
- The frontend builds with the existing locked Node/Vite dependencies, then copies only compiled assets into an Alpine Nginx runtime. Node, npm, and source files are absent from that runtime. Nginx runs as UID/GID 10001 on 8080, stores configuration/PID/temp files under /tmp, and uses a dedicated /healthz process probe.
- Production startup requires Secure cookies, an explicit lowercase APP_HOST without a port, and a PostgreSQL URL with sslmode=verify-full plus an existing absolute CA file. The image contains a checksum-reviewed public RDS CA snapshot; the test uses an ephemeral local CA mounted separately. No TLS-verification bypass is provided.
- Proxy trust is specific to ALB -> frontend -> API. The API accepts only a loopback peer, trusts two tail X-Forwarded-For hops and one normalized scheme, and ignores forwarded host/port/prefix. The frontend accepts only the reviewed hostname for application routes, appends its proxy peer to the client chain, and normalizes HTTPS. ALB security-group restrictions remain essential: arbitrary clients must never reach the frontend directly. Re-review the hop count before adding another proxy.
- Private-IP/loopback health checks expose only the existing liveness/readiness responses and do not require forwarded HTTPS headers. Other API traffic requires the reviewed host, HTTPS, and proxy chain.
- The static server supplies CSP without unsafe-inline/unsafe-eval, nosniff, frame denial, referrer and permissions policies, and HSTS on forwarded HTTPS responses. Only successful hashed assets are cached immutably; HTML, API responses, and errors are no-store. API/frontend access logs omit URLs, query strings, credentials, cookies, and request bodies. SQLAlchemy hides bound parameters in errors.
- API and frontend roots are read-only with writable temporary storage only, all Linux capabilities dropped, and no-new-privileges in the local harness. ECS already drops capabilities and uses read-only roots; the Fargate platform's privilege model remains subject to live verification.

## Initialization and database rights

Production API startup never migrates or seeds. The disposable stack uses an explicit setup-profile administrative container before API startup. Separate random credentials identify the migration/fixture administrator and the runtime user.

| Runtime access | Grant model |
|---|---|
| Users | SELECT plus UPDATE of password_hash/updated_at for hash upgrades; no account creation or role changes |
| Findings | SELECT plus UPDATE of status/resolution_reason/updated_by/version/updated_at; no ingestion or deletion |
| Notes and audit events | SELECT and INSERT only |
| Server sessions and throttle buckets | SELECT/INSERT/UPDATE/DELETE for lifecycle and expiry cleanup |
| Schema/roles | No ownership, schema creation, superuser, database creation, role creation, replication, or RLS bypass |

The grant helper explicitly rejects use outside the disposable db hostname/database and test mode. These grants are not applied to AWS. A future RDS migration/runtime design must be reviewed for its exact roles, ownership, tables, and upgrade procedures. PostgreSQL ACLs enforce append-only behavior against the runtime identity; the database owner remains privileged.

## Evidence and limits

The CI smoke runs the actual production images behind an ephemeral HTTPS edge and a TLS-enabled PostgreSQL instance. It verifies certificate trust, Secure cookies, origin/host rejection, static headers/assets, authenticated analyst/viewer/CSRF/concurrency/note/history/logout workflows, actual database denials, TLS usage, UID, mount flags, capabilities, no-new-privileges, and loopback binding. It also checks the default development stack. Required image checks scan both variants; the check names and main ruleset do not change.

No AWS IAM or RDS runtime behavior, live certificate/DNS, real user data, or browser walkthrough is implied by this fixture. ALB-to-frontend traffic remains private HTTP. Account/region/budget, registry publication, remote state, live secret rotation, operational alerts, backup recovery, and retention/teardown approval remain outstanding. Existing infrastructure exceptions and their dates remain in ADR 0003.

## References

- [Flask production deployment](https://flask.palletsprojects.com/en/stable/deploying/)
- [Flask proxy trust](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/)
- [Gunicorn release source](https://github.com/benoitc/gunicorn/tree/26.2.0)
- [Nginx proxy header behavior](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [PostgreSQL privileges](https://www.postgresql.org/docs/18/ddl-priv.html)

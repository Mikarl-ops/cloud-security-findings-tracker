# Local release checklist

The release candidate is a local portfolio demo for investigating synthetic cloud findings. This record covers [main at `6fe3455`](https://github.com/Mikarl-ops/cloud-security-findings-tracker/commit/6fe34557c828223f96846e9adf84411d50ab829d), verified on 2026-11-04.

## Verification record

| Check | Evidence |
|---|---|
| Required checks on `main` | All 11 jobs passed on the recorded commit. [Quality](https://github.com/Mikarl-ops/cloud-security-findings-tracker/actions/runs/41785124730) · [Security](https://github.com/Mikarl-ops/cloud-security-findings-tracker/actions/runs/41785124607) |
| Fresh checkout with PostgreSQL and Compose | A hosted Ubuntu runner built and started the default stack from a clean checkout using ephemeral environment values. It verified migrations, found all six seed records on reseeding, and checked sessions, CSRF, role enforcement, notes, audit history, and logout through the frontend proxy. [Compose job](https://github.com/Mikarl-ops/cloud-security-findings-tracker/actions/runs/41785124730/job/126425403240) |
| Production image smoke | The same hosted job exercised HTTPS, verified database TLS, and checked restricted runtime permissions using disposable containers. [Production image verification](production-images.md) |
| Human-facing investigation workflow | Chromium verified the analyst workflow through resolution, then checked that a viewer could read the note, reason, and three activity entries. This browser run used the React and Flask app with in-memory SQLite. [Walkthrough and screenshots](portfolio-walkthrough.md) |
| Clean Windows clone | All 38 backend tests passed using the existing Python environment with imports from the clean clone. A fresh `npm ci` install passed all 10 frontend tests and built successfully. The API contract, Markdown links, tracked-file hygiene, and public CA snapshot also passed validation. |

The hosted job exercises the README's Compose build and startup path. It supplies configuration through the job environment and creates synthetic test accounts and a separate finding for its HTTP checks. The README uses a local `.env` and an interactive password prompt. A manual browser run against that exact PostgreSQL setup still requires a Docker-capable workstation.

## Repeat from a fresh checkout

1. Check out the candidate revision. Follow the [README setup](../README.md#start-the-local-application) on a machine with Docker Compose v2. Use a disposable database and set fresh local credentials in `.env`.
2. Confirm readiness at <http://localhost:5000/api/v1/health/ready>. Verify the schema and seed from the repository root. A fresh stack reports `0 added, 6 already present` on reseeding.

   ```text
   docker compose exec -T api flask --app tracker:create_app db check
   docker compose exec -T api flask --app tracker:create_app seed-demo
   ```

3. Create the local analyst and viewer accounts as described in the [investigation playbook](investigation-playbook.md). Open <http://localhost:5173> and follow the exercise. Confirm the resolution reason, note, and ordered history persist across sign-out and sign-in as the viewer.
4. Check the Quality and Security workflows on the candidate commit. Record the commit and run links with the result. For production image changes, also repeat the [disposable HTTPS test](production-images.md).
5. Stop the stack using the README cleanup steps. Remove volumes only when the database is disposable and its data can be discarded.

## Known limits and follow-ups

- The tracker uses synthetic findings in a single workspace with analyst and viewer roles. Live telemetry ingestion, automated response, multi-tenancy, and identity federation are outside the local demo's scope.
- The PostgreSQL integration and Chromium walkthrough were verified separately. The local single-node setup does not provide production backup or availability guarantees.
- Dependabot PRs [#5](https://github.com/Mikarl-ops/cloud-security-findings-tracker/pull/5) through [#9](https://github.com/Mikarl-ops/cloud-security-findings-tracker/pull/9) remain open. Their [review notes](dependency-review.md) record the Node requirement for jsdom and the Vite bundler change. Review each against the current `main` before merging.
- Recheck the minimatch override by 2026-11-07. Review the development-bind and Terraform scanner exceptions by 2026-11-30 or before live exposure, as applicable. See the [CI and security policy](ci-security.md).
- Optional AWS work requires separate approval and an account, region, budget, protected Terraform state, deployment roles, immutable images, live database identities, DNS and certificate validation, monitoring, and a teardown plan. See the [deployment prerequisites](deployment.md#prerequisites-before-live-aws-work).

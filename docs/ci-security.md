# Automated quality and security

GitHub Actions runs the `Quality` and `Security` workflows for pull requests into `main`, pushes to `main`, and manual runs. Security also runs weekly on Monday at 03:23 UTC (11:23 Singapore time), once the workflow is on the default branch. Dependency advisory databases change over time; a later run can fail without a source change.

## Checks and failure conditions

| Check name | What fails the check |
|---|---|
| Backend tests and lint | Ruff findings, failing pytest cases, dependency conflicts, or installation errors |
| Frontend tests and build | ESLint, TypeScript, Vitest, installation, or build errors |
| API contract and workflow validation | Invalid contract invariants, broken local documentation links, tracked environment files, or actionlint errors |
| PostgreSQL and Compose smoke | Image/startup failures, schema drift, non-idempotent seeding, or a failed HTTP workflow assertion |
| Python static analysis | Bandit findings with severity and confidence both medium or higher |
| Python dependency audit | Any known advisory in the application or scanner lock, or incomplete dependency collection |
| Frontend dependency audit | High or critical advisories, or an audit/registry error; lower findings remain visible in the job log |
| Repository secret scan | Any Gitleaks detection across all fetched Git history; output is fully redacted |
| Container scan (api) | High or critical OS or package vulnerabilities, including unfixed findings, or scanner/build errors |
| Container scan (frontend) | The same gate for the frontend development image |
| Container scan (db) | The same gate for the derived PostgreSQL image |

No check uses `continue-on-error`, an advisory ignore list, or an unfixed-vulnerability exclusion. A failed scanner or database download fails its check rather than reporting a clean scan.

## Pipeline trust boundary

- Workflows run on disposable GitHub-hosted Ubuntu runners with `contents: read`. They use `pull_request`, without privileged `pull_request_target` execution.
- Actions are pinned to full commit IDs, with release versions beside each pin. Checkout does not persist its credential.
- actionlint 1.7.12, Gitleaks 8.30.1, and Trivy 0.76.1 archives are checked against committed SHA-256 digests before execution. Python scanner dependencies are fully version-pinned in [requirements-security.txt](../scripts/requirements-security.txt).
- Jobs have timeouts, and a newer update cancels outdated checks for the same PR. The container matrix completes each service independently so all results are visible.
- The Compose job generates and masks random local credentials for each run. It creates no `.env` file, uses no repository secrets or AWS identity, and removes its containers, network, and database volume afterward.
- Application images are built for tests and scanning. They are not published or deployed.

The Compose smoke test checks the UI response and exercises JSON requests through Vite's same-origin proxy. It verifies PostgreSQL readiness, migrations, seed idempotence, session login/logout, missing-CSRF rejection, viewer write rejection, analyst status changes, stale-version rejection, notes, and audit history. It is an HTTP integration test. The separate frontend test suite verifies rendering and interactions, including HTML-like text staying inert.

## Image maintenance

The API uses Python 3.12 on Alpine 3.24 and the application lock. All three Dockerfiles apply available Alpine package updates. The frontend removes npm after its locked install and starts Vite directly with Node. PostgreSQL starts directly as its existing `postgres` user; its unused `gosu` helper and embedded Go runtime are removed. The other services also run as non-root users.

The PostgreSQL 18 named volume mounts at `/var/lib/postgresql`, matching its versioned data layout. Do not point a populated older-major database volume at a new major version without a backup and migration plan.

Base image tags and OS repositories receive security updates. Application packages, actions, and scanner versions are pinned, but complete image bit-for-bit reproducibility is not claimed. CI builds with `--pull` and scans the resulting images. Any future digest pinning must include a process for updating and rescanning those digests.

## Local reproduction

Use the backend virtual environment and run these commands from `backend/`:

```text
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m pip check
python -m ruff check --config pyproject.toml src tests start_dev.py ../scripts
python -m pytest -q
```

From `frontend/`, run `npm ci`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, and `npm audit --audit-level=high`.

From the repository root, use a separate activated Python 3.12 virtual environment for scanner dependencies:

```text
python -m pip install -r scripts/requirements-security.txt
python scripts/validate_contract.py
python -m bandit -r backend/src scripts backend/start_dev.py -ll -ii
python -m pip_audit --strict --disable-pip --no-deps -r backend/requirements.lock
python -m pip_audit --strict --disable-pip --no-deps -r scripts/requirements-security.txt
```

Install the workflow-pinned versions of actionlint, Gitleaks, and Trivy using the official release archives and digests in the workflows. Run `actionlint`, `gitleaks git --redact=100 --log-opts="--all" .`, and the same `trivy image` command as CI against locally built images.

For the integration test, start a **disposable** Compose stack using the [local setup](../README.md). Run `docker compose exec -T api flask --app tracker:create_app db check`, then `python scripts/smoke_test.py`. The script creates two synthetic accounts and one finding, then adds a status change, note, and audit records. It is intended for a database that can be discarded after testing.

## Open findings and exceptions

### Development dependency: minimatch

On 2026-10-31, npm reported 12 moderate dependency findings associated with [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249). They originate from `minimatch` 10.2.6 in the ESLint/TypeScript lint dependency graph. The advisory's fix is in 11.0.1; the current consumers require the earlier major version.

The potential impact is denial of service when processing crafted glob patterns during development or CI. This package is not part of the built React application. CI limits execution time and uses disposable runners with read-only repository access. The finding remains visible in job output and is below the documented npm gate. The maintainer should review upstream compatible fixes by **2026-11-07**. Do not force a major transitive override without checking API compatibility and rerunning lint, tests, and builds.

### Bandit B104: development-container bind

`backend/start_dev.py` has one targeted `# nosec B104` for the fixed `0.0.0.0` development bind. The process must accept requests from the frontend container. Compose publishes the API only to host loopback, and this entrypoint is not suitable for a public deployment. No other Bandit rule is disabled. Review this exception before any deployment or by **2026-11-30**, whichever comes first.

## Review and merge settings

The active [Protect main ruleset](https://github.com/Mikarl-ops/cloud-security-findings-tracker/rules/26267100) was verified on 2026-10-31. It targets only `refs/heads/main`, requires a pull request, requires the eleven checks above from GitHub Actions, and requires the branch to be up to date before merging. It blocks force pushes and deletion, requires review conversations to be resolved, and has no bypass actors. The required approving-review count is zero so a solo maintainer can merge; the agent still needs the owner's explicit merge approval.

The importable configuration is recorded in [main.json](../.github/rulesets/main.json). Editing that file alone does not update GitHub settings: an administrator must review and apply the change, then verify the live rule. Keep the check names and GitHub Actions integration ID consistent with the workflows.

Dependabot proposes weekly action, npm, backend Python, and scanner dependency updates. Python update PRs must keep `pyproject.toml` and the complete `backend/requirements.lock` consistent; Dependabot is not a substitute for regenerating and reviewing that custom lock. Rerun audits and tests for dependency updates. Scanner requirements are similarly resolved in a clean environment and frozen in full.

Terraform validation and infrastructure scanning belong to the next delivery stage, after Terraform exists. No cloud provisioning is part of these checks.

## References

- [GitHub Actions security](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [actionlint](https://github.com/rhysd/actionlint)
- [Bandit command reference](https://bandit.readthedocs.io/en/latest/man/bandit.html)
- [pip-audit](https://github.com/pypa/pip-audit)
- [Gitleaks](https://github.com/gitleaks/gitleaks)
- [Trivy](https://trivy.dev/)
- [Official PostgreSQL image and volume layout](https://hub.docker.com/_/postgres)

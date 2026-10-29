# Backend

The Flask API uses PostgreSQL, Alembic migrations, Argon2id password hashes, server-side sessions, CSRF tokens, and analyst/viewer authorization. It accepts only synthetic findings. Database and authentication behavior are local-only in this milestone; deployment and AWS are out of scope.

## Local setup

From the repository root, copy `.env.example` to `.env`, then replace `POSTGRES_PASSWORD` and `SECRET_KEY` with distinct random local-only values. Keep the password in `DATABASE_URL` consistent with `POSTGRES_PASSWORD`. Flask's CLI loads `.env` through the pinned `python-dotenv` dependency.

Start PostgreSQL with `docker compose up -d db`. In this directory, create and activate a Python 3.12 virtual environment, then install the pinned dependencies and package:

```text
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m flask --app tracker:create_app db upgrade
python -m flask --app tracker:create_app create-user analyst --role analyst
python -m flask --app tracker:create_app run --host 127.0.0.1
```

The account command prompts for a password and stores only its Argon2id hash. `GET /api/v1/auth/csrf` provides the token required in `X-CSRFToken` for login and other state-changing requests. The session cookie is HttpOnly, host-only, and SameSite=Lax; set `SESSION_COOKIE_SECURE=true` when running over HTTPS.

## Validation

Run `python -m pytest` and `ruff check .` from this directory. Tests use an isolated SQLite database and synthetic records; they do not require Docker, PostgreSQL, AWS, or public service calls.


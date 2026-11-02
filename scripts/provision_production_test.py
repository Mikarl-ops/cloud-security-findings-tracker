"""Grant runtime permissions in the disposable TLS Compose database, never a live database."""

import os
import re

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url


def main() -> None:
    url = make_url(os.environ["DATABASE_URL"])
    password = os.environ.get("RUNTIME_DB_PASSWORD", "")
    if (
        os.environ.get("DISPOSABLE_PRODUCTION_TEST") != "1"
        or url.host != "db"
        or url.database != "tracker"
        or not re.fullmatch("[a-f0-9]{64}", password)
    ):
        raise SystemExit("This helper is restricted to the disposable production test.")
    connection_url = url.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(connection_url, autocommit=True) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", ("tracker_runtime",)
        ).fetchone()
        action = sql.SQL("ALTER") if exists else sql.SQL("CREATE")
        connection.execute(
            sql.SQL(
                "{} ROLE tracker_runtime LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
            ).format(action, sql.Literal(password))
        )
        connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        for statement in (
            "GRANT CONNECT ON DATABASE tracker TO tracker_runtime",
            "GRANT USAGE ON SCHEMA public TO tracker_runtime",
            "GRANT SELECT ON users, findings, finding_notes, audit_events TO tracker_runtime",
            "GRANT UPDATE (password_hash, updated_at) ON users TO tracker_runtime",
            "GRANT UPDATE (status, resolution_reason, updated_by, version, updated_at) "
            "ON findings TO tracker_runtime",
            "GRANT INSERT ON finding_notes, audit_events TO tracker_runtime",
            "GRANT SELECT, INSERT, UPDATE, DELETE ON server_sessions, auth_throttle_buckets "
            "TO tracker_runtime",
        ):
            connection.execute(statement)
    print("Disposable runtime role granted only the reviewed application permissions.")


if __name__ == "__main__":
    main()

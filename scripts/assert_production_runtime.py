"""Check actual database permissions and container restrictions in the disposable API."""

import errno
import os
import tempfile
from pathlib import Path

import psycopg
from sqlalchemy.engine import make_url


def main() -> None:
    assert os.environ.get("DISPOSABLE_PRODUCTION_TEST") == "1"
    assert os.getuid() == 10001
    status = dict(
        line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines()
        if ":" in line
    )
    assert int(status["CapEff"].strip(), 16) == 0
    assert status["NoNewPrivs"].strip() == "1"
    roots = [line.split() for line in Path("/proc/mounts").read_text().splitlines()]
    assert any(parts[1] == "/" and "ro" in parts[3].split(",") for parts in roots)
    with tempfile.TemporaryFile() as stream:
        stream.write(b"synthetic writable temporary data")
    try:
        Path("/app/unexpected-write").write_text("synthetic")
    except OSError as error:
        assert error.errno in {errno.EROFS, errno.EACCES}
    else:
        raise AssertionError("The application root must not be writable.")
    assert not Path("/app/backend/start_dev.py").exists()
    listeners = Path("/proc/net/tcp").read_text().splitlines()[1:]
    bound = [line.split()[1] for line in listeners if line.split()[3] == "0A"]
    assert "0100007F:1F40" in bound
    assert "00000000:1F40" not in bound

    url = make_url(os.environ["DATABASE_URL"]).set(drivername="postgresql")
    with psycopg.connect(url.render_as_string(hide_password=False), autocommit=True) as conn:
        role = conn.execute(
            "SELECT current_user, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls "
            "FROM pg_roles WHERE rolname = current_user"
        ).fetchone()
        assert role == ("tracker_runtime", False, False, False, False)
        assert conn.execute(
            "SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()"
        ).fetchone()[0]
        assert not conn.execute(
            "SELECT has_schema_privilege(current_user, 'public', 'CREATE')"
        ).fetchone()[0]
        assert not conn.execute(
            "SELECT has_table_privilege(current_user, 'users', 'INSERT')"
        ).fetchone()[0]
        for statement in (
            "UPDATE audit_events SET event_type = event_type WHERE FALSE",
            "DELETE FROM audit_events WHERE FALSE",
            "UPDATE users SET role = role WHERE FALSE",
            "DELETE FROM finding_notes WHERE FALSE",
        ):
            try:
                conn.execute(statement)
            except psycopg.errors.InsufficientPrivilege:
                pass
            else:
                raise AssertionError("A forbidden database operation was accepted.")
    print("Production runtime passed: TLS, limited DB grants, append-only audit/notes, non-root, "
          "read-only root, dropped capabilities, no-new-privileges, and loopback API.")


if __name__ == "__main__":
    main()

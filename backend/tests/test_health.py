from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from conftest import login
from tracker.extensions import db


def test_liveness_reports_only_process_state(app, client):
    with app.app_context():
        db.drop_all()

    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert "database" not in response.get_json()


def test_readiness_requires_database_and_migrated_tables(client):
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ready"}


def test_readiness_rejects_missing_tables(app, client):
    with app.app_context():
        db.drop_all()

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.get_json() == {"status": "unavailable"}


def test_health_probes_with_session_cookie_during_database_failure(app, client):
    login(client)
    with app.app_context():
        engine = db.engine

    def fail_query(*_args):
        raise OperationalError(None, None, RuntimeError("synthetic database failure"))

    event.listen(engine, "before_cursor_execute", fail_query)
    try:
        live = client.get("/api/v1/health/live")
        ready = client.get("/api/v1/health/ready")
    finally:
        event.remove(engine, "before_cursor_execute", fail_query)

    assert live.status_code == 200
    assert live.get_json() == {"status": "ok"}
    assert ready.status_code == 503
    assert ready.get_json() == {"status": "unavailable"}
    assert client.get("/api/v1/health/ready").get_json() == {"status": "ready"}
    assert client.get("/api/v1/auth/session").status_code == 200

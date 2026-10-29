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

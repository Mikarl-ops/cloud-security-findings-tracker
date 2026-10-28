from tracker import create_app


def test_liveness_reports_only_process_state():
    client = create_app().test_client()

    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


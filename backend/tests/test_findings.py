"""Authorization, filtering, status workflow, notes, and audit behavior."""

import pytest
from sqlalchemy import event, func, select

from conftest import csrf_token, login
from tracker.extensions import db
from tracker.models import AuditEvent, FindingNote


def test_finding_reads_require_authentication(client):
    assert client.get("/api/v1/findings").status_code == 401
    assert client.get("/api/v1/findings/summary").status_code == 401


def test_list_and_detail_return_only_allowlisted_metadata(client):
    login(client, "viewer")
    listed = client.get("/api/v1/findings?status=new&severity=medium&page=1&page_size=25")
    finding_id = listed.get_json()["items"][0]["id"]
    detail = client.get(f"/api/v1/findings/{finding_id}").get_json()

    assert listed.status_code == 200
    assert listed.get_json()["total"] == 1
    assert detail["metadata"] == {"region": "ap-southeast-1"}
    assert "password" not in detail["metadata"]


def test_viewer_cannot_change_finding_status(client, app):
    login(client, "viewer")
    token = csrf_token(client)
    response = client.patch(
        f"/api/v1/findings/{app.config['TEST_FINDING_ID']}",
        json={"status": "investigating", "expected_version": 1},
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 403


def test_analyst_status_change_note_and_history_are_audited(client, app):
    login(client)
    token = csrf_token(client)
    finding_url = f"/api/v1/findings/{app.config['TEST_FINDING_ID']}"
    changed = client.patch(
        finding_url,
        json={"status": "investigating", "expected_version": 1},
        headers={"X-CSRFToken": token},
    )
    assert changed.status_code == 200
    assert changed.get_json()["version"] == 2

    stale = client.patch(
        finding_url,
        json={"status": "investigating", "expected_version": 1},
        headers={"X-CSRFToken": token},
    )
    assert stale.status_code == 409

    token = csrf_token(client)
    note = client.post(
        f"{finding_url}/notes",
        json={"body": "Synthetic triage note: review adjacent identity activity."},
        headers={"X-CSRFToken": token},
    )
    assert note.status_code == 201

    notes = client.get(f"{finding_url}/notes").get_json()["items"]
    history = client.get(f"{finding_url}/history").get_json()["items"]
    assert notes[0]["body"].startswith("Synthetic triage note")
    assert [event["event_type"] for event in history] == [
        "finding.status_changed",
        "finding.note_added",
    ]
    assert history[1]["details"] == {"note_id": note.get_json()["id"]}


def test_resolution_requires_reason_and_invalid_transition_is_rejected(client, app):
    login(client)
    token = csrf_token(client)
    url = f"/api/v1/findings/{app.config['TEST_FINDING_ID']}"
    invalid = client.patch(
        url,
        json={"status": "resolved", "expected_version": 1, "resolution_reason": ""},
        headers={"X-CSRFToken": token},
    )
    assert invalid.status_code == 422

    not_allowed = client.patch(
        url,
        json={"status": "resolved", "expected_version": 1, "resolution_reason": "false positive"},
        headers={"X-CSRFToken": token},
    )
    assert not_allowed.status_code == 422


def test_note_and_audit_event_roll_back_together(client, app):
    login(client)
    token = csrf_token(client)

    def reject_audit(_mapper, _connection, _target):
        raise RuntimeError("test-only audit failure")

    event.listen(AuditEvent, "before_insert", reject_audit)
    try:
        response = client.post(
            f"/api/v1/findings/{app.config['TEST_FINDING_ID']}/notes",
            json={"body": "This note must roll back."},
            headers={"X-CSRFToken": token},
        )
    finally:
        event.remove(AuditEvent, "before_insert", reject_audit)

    assert response.status_code == 500
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(FindingNote)) == 0


def test_invalid_filters_and_pagination_are_bounded(client):
    login(client, "viewer")
    assert client.get("/api/v1/findings?unknown=value").status_code == 400
    assert client.get("/api/v1/findings?page_size=101").status_code == 400
    assert client.get("/api/v1/findings?observed_from=2026-01-14T08:30:00").status_code == 400
    assert client.get(
        "/api/v1/findings?observed_from=2026-01-15T00:00:00Z&observed_to=2026-01-14T00:00:00Z"
    ).status_code == 400


def test_out_of_range_page_returns_empty_results(client, app):
    login(client)
    finding_url = f"/api/v1/findings/{app.config['TEST_FINDING_ID']}"
    page = 10**30

    for path in ("/api/v1/findings", f"{finding_url}/notes", f"{finding_url}/history"):
        response = client.get(path, query_string={"page": page, "page_size": 100})
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["items"] == []
        assert payload["page"] == page


@pytest.mark.parametrize(
    ("body", "content_type", "expected"),
    [
        ('{"body":"valid"}', "text/plain", 415),
        ('{"body":', "application/json", 400),
        ('["not an object"]', "application/json", 422),
        ('{"body":"' + "x" * (16 * 1024) + '"}', "application/json", 413),
    ],
)
def test_note_rejects_invalid_request_bodies(client, app, body, content_type, expected):
    login(client)
    response = client.post(
        f"/api/v1/findings/{app.config['TEST_FINDING_ID']}/notes",
        data=body,
        content_type=content_type,
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == expected
    assert response.mimetype == "application/problem+json"
    assert response.get_json()["request_id"] == response.headers["X-Request-ID"]
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(FindingNote)) == 0
        assert db.session.scalar(select(func.count()).select_from(AuditEvent)) == 0

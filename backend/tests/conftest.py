"""Isolated database and synthetic accounts for API tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from tracker import create_app
from tracker.extensions import db
from tracker.models import Finding, User

TEST_SECRET = "test-only-secret-value-with-at-least-32-characters"
TEST_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def app():
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": TEST_SECRET,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SESSION_COOKIE_SECURE": False,
            "AUTH_RATE_LIMIT_FAILURES": 3,
            "AUTH_RATE_LIMIT_WINDOW_SECONDS": 60,
        }
    )
    hasher = application.extensions["password_hasher"]
    with application.app_context():
        db.create_all()
        analyst = User(
            username="analyst",
            password_hash=hasher.hash(TEST_PASSWORD),
            role="analyst",
            is_active=True,
        )
        viewer = User(
            username="viewer",
            password_hash=hasher.hash(TEST_PASSWORD),
            role="viewer",
            is_active=True,
        )
        inactive = User(
            username="inactive",
            password_hash=hasher.hash(TEST_PASSWORD),
            role="analyst",
            is_active=False,
        )
        finding = Finding(
            id=uuid4(),
            source="cloudtrail",
            source_event_id="synthetic-test-event",
            title="Repeated failed console sign-ins",
            description="Synthetic test finding.",
            evidence_summary="Several synthetic failed sign-ins.",
            metadata_json={"region": "ap-southeast-1", "password": "must-not-be-returned"},
            severity="medium",
            status="new",
            observed_at=datetime(2026, 1, 14, 8, 30, tzinfo=UTC),
        )
        db.session.add_all([analyst, viewer, inactive, finding])
        db.session.commit()
        application.config["TEST_FINDING_ID"] = str(finding.id)

    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def csrf_token(client) -> str:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def login(client, username: str = "analyst", password: str = TEST_PASSWORD) -> None:
    token = csrf_token(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200, response.get_json()

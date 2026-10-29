"""Authentication, session rotation, CSRF, and throttling behavior."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from conftest import TEST_PASSWORD, csrf_token
from tracker import create_app
from tracker.extensions import db
from tracker.models import ServerSession, User


def test_login_uses_generic_failure_for_unknown_and_inactive_users(client):
    token = csrf_token(client)
    headers = {"X-CSRFToken": token}
    unknown = client.post(
        "/api/v1/auth/login",
        json={"username": "not-a-user", "password": TEST_PASSWORD},
        headers=headers,
    )
    inactive = client.post(
        "/api/v1/auth/login",
        json={"username": "inactive", "password": TEST_PASSWORD},
        headers=headers,
    )

    assert unknown.status_code == inactive.status_code == 401
    assert unknown.get_json()["title"] == inactive.get_json()["title"]
    assert unknown.get_json()["detail"] == inactive.get_json()["detail"]


def test_login_rotates_session_and_logout_invalidates_it(client):
    token = csrf_token(client)
    old_cookie = client.get_cookie("csft_session").value
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "analyst", "password": TEST_PASSWORD},
        headers={"X-CSRFToken": token},
    )
    new_cookie = client.get_cookie("csft_session").value

    assert response.status_code == 200
    assert old_cookie != new_cookie
    assert "HttpOnly" in response.headers["Set-Cookie"]
    assert "SameSite=Lax" in response.headers["Set-Cookie"]
    assert client.get("/api/v1/auth/session").get_json()["user"]["role"] == "analyst"

    assert client.post("/api/v1/auth/logout").status_code == 403
    token = csrf_token(client)
    logout_response = client.post("/api/v1/auth/logout", headers={"X-CSRFToken": token})
    assert logout_response.status_code == 204
    assert client.get("/api/v1/auth/session").status_code == 401


def test_server_session_stores_hashed_id_and_absolute_expiry(client, app):
    csrf_token_value = csrf_token(client)
    client.post(
        "/api/v1/auth/login",
        json={"username": "analyst", "password": TEST_PASSWORD},
        headers={"X-CSRFToken": csrf_token_value},
    )
    session_id = client.get_cookie("csft_session").value
    sid_hash = hashlib.sha256(f"csft:{session_id}".encode()).hexdigest()

    with app.app_context():
        record = db.session.get(ServerSession, sid_hash)
        assert record is not None
        assert session_id not in record.sid_hash
        payload = json.loads(record.data)
        absolute_expiry = datetime.fromisoformat(payload["_absolute_expires_at"])
        stored_expiry = record.expiry
        if stored_expiry.tzinfo is None:
            stored_expiry = stored_expiry.replace(tzinfo=UTC)
        assert datetime.now(UTC) < stored_expiry <= absolute_expiry


def test_expired_server_session_is_unauthenticated(client, app):
    csrf_token_value = csrf_token(client)
    client.post(
        "/api/v1/auth/login",
        json={"username": "analyst", "password": TEST_PASSWORD},
        headers={"X-CSRFToken": csrf_token_value},
    )
    session_id = client.get_cookie("csft_session").value
    sid_hash = hashlib.sha256(f"csft:{session_id}".encode()).hexdigest()
    with app.app_context():
        record = db.session.get(ServerSession, sid_hash)
        record.expiry = datetime.now(UTC) - timedelta(seconds=1)
        db.session.commit()

    assert client.get("/api/v1/auth/session").status_code == 401


def test_login_requires_csrf_and_rate_limits_failures(client):
    response = client.post(
        "/api/v1/auth/login", json={"username": "analyst", "password": "wrong-password"}
    )
    assert response.status_code == 403

    token = csrf_token(client)
    invalid_token = client.post(
        "/api/v1/auth/login",
        json={"username": "analyst", "password": "wrong-password"},
        headers={"X-CSRFToken": "invalid-token"},
    )
    assert invalid_token.status_code == 403
    headers = {"X-CSRFToken": token}
    for _ in range(3):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "analyst", "password": "wrong-password"},
            headers=headers,
        )
        assert response.status_code == 401

    limited = client.post(
        "/api/v1/auth/login",
        json={"username": "analyst", "password": "wrong-password"},
        headers=headers,
    )
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0


def test_create_user_cli_prompts_and_hashes_password(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-user", "new-analyst", "--role", "analyst"],
        input="a-strong-local-password\na-strong-local-password\n",
    )

    assert result.exit_code == 0, result.output
    assert "a-strong-local-password" not in result.output
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "new-analyst"))
        assert user.password_hash.startswith("$argon2id$")


def test_protected_session_endpoint_requires_authentication(client):
    response = client.get("/api/v1/auth/session")

    assert response.status_code == 401
    assert response.mimetype == "application/problem+json"


def test_production_configuration_requires_secure_session_cookie():
    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE"):
        create_app(
            {
                "SECRET_KEY": "test-only-secret-value-with-at-least-32-characters",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "APP_ENV": "production",
                "SESSION_COOKIE_SECURE": False,
            }
        )

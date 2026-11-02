"""Production settings reject unsafe URLs, untrusted hosts, and spoofed proxy paths."""

import pytest
from flask import jsonify, request

from tracker import create_app


@pytest.fixture
def production_settings(tmp_path):
    ca = tmp_path / "test-ca.crt"
    ca.write_text("Synthetic unit-test placeholder; TLS verification is tested in Compose.")
    return {
        "TESTING": True,
        "APP_ENV": "production",
        "APP_HOST": "tracker.example.invalid",
        "SECRET_KEY": "synthetic-unit-test-key-at-least-32-characters",
        "SESSION_COOKIE_SECURE": True,
        "SQLALCHEMY_DATABASE_URI": (
            "postgresql+psycopg://synthetic:unused@db/tracker"
            f"?sslmode=verify-full&sslrootcert={ca.as_posix()}"
        ),
    }


@pytest.mark.parametrize("host", [None, "", "*", "Example.com", "example.com:443", "x;return 200"])
def test_production_requires_explicit_safe_host(production_settings, host):
    production_settings["APP_HOST"] = host
    with pytest.raises(RuntimeError, match="APP_HOST"):
        create_app(production_settings)


@pytest.mark.parametrize(
    "url",
    [
        "sqlite://",
        "postgresql+psycopg://synthetic:unused@db/tracker?sslmode=require",
        "postgresql+psycopg://synthetic:unused@db/tracker?sslmode=verify-full",
        "postgresql+psycopg://synthetic:unused@db/tracker"
        "?sslmode=verify-full&sslrootcert=/nonexistent-test-ca",
    ],
)
def test_production_requires_verified_database_tls(production_settings, url):
    production_settings["SQLALCHEMY_DATABASE_URI"] = url
    with pytest.raises(RuntimeError, match="verify-full"):
        create_app(production_settings)


def test_proxy_trust_uses_tail_hops_and_ignores_forwarded_host(production_settings):
    app = create_app(production_settings)

    @app.get("/proxy-probe")
    def probe():
        return jsonify(client=request.remote_addr, host=request.host, scheme=request.scheme)

    client = app.test_client()
    response = client.get(
        "/proxy-probe",
        base_url="http://tracker.example.invalid",
        headers={
            "X-Forwarded-For": "198.51.100.99, 203.0.113.10, 10.42.0.10",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "attacker.example.invalid",
            "X-Forwarded-Port": "9999",
        },
    )
    assert response.status_code == 200
    assert response.json == {
        "client": "203.0.113.10", "host": "tracker.example.invalid", "scheme": "https",
    }


def test_production_rejects_direct_or_incomplete_proxy_requests(production_settings):
    client = create_app(production_settings).test_client()
    path = "/api/v1/health/live"
    assert client.get(path, base_url="http://127.0.0.1").status_code == 200
    assert client.get(
        path, base_url="http://tracker.example.invalid",
        environ_overrides={"REMOTE_ADDR": "203.0.113.10"},
        headers={"X-Forwarded-For": "203.0.113.10, 10.42.0.10", "X-Forwarded-Proto": "https"},
    ).status_code == 403
    assert client.get(
        "/proxy-probe", base_url="http://tracker.example.invalid",
        headers={"X-Forwarded-Proto": "https", "X-Forwarded-For": "203.0.113.10"},
    ).status_code == 400
    assert client.get(
        "/proxy-probe", base_url="http://tracker.example.invalid",
        headers={"X-Forwarded-For": "203.0.113.10, 10.42.0.10"},
    ).status_code == 400
    assert client.get(path, base_url="http://attacker.example.invalid").status_code == 400

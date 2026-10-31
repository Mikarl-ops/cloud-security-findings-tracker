"""Exercise the disposable Compose stack through Vite's same-origin API proxy.

Creates synthetic accounts and a finding in the Compose database. Run only against
a disposable local stack; CI removes that stack and its volume after the test.
"""

from __future__ import annotations

import json
import secrets
import subprocess
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE_URL = "http://127.0.0.1:5173"
SETUP_FIXTURE = """
import json
import sys
from datetime import UTC, datetime
from tracker import create_app
from tracker.extensions import db
from tracker.models import Finding, User

fixture = json.load(sys.stdin)
app = create_app()
with app.app_context():
    for role in ('analyst', 'viewer'):
        db.session.add(User(
            username=fixture[role], role=role, is_active=True,
            password_hash=app.extensions['password_hasher'].hash(fixture['password']),
        ))
    finding = Finding(
        source='demo', source_event_id='synthetic-smoke-' + fixture['nonce'],
        title='Synthetic CI finding', description='Fabricated integration fixture.',
        evidence_summary='No real telemetry.', metadata_json={'region': 'ap-southeast-1'},
        severity='medium', status='new', observed_at=datetime.now(UTC),
    )
    db.session.add(finding)
    db.session.commit()
    print(finding.id)
"""


class ApiClient:
    def __init__(self) -> None:
        self.cookies = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: int = 200,
        payload: dict | None = None,
        csrf: str | None = None,
    ) -> dict:
        headers = {"Accept": "application/json"}
        if csrf:
            headers["X-CSRFToken"] = csrf
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        request = Request(BASE_URL + "/api/v1" + path, data=body, headers=headers, method=method)
        try:
            response = self.opener.open(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise AssertionError(f"{method} {path}: expected {expected}, got {response.status}")
            raw = response.read()
            return json.loads(raw) if raw else {}

    def token(self) -> str:
        return self.request("GET", "/auth/csrf")["csrf_token"]

    def login(self, username: str, password: str) -> None:
        self.request(
            "POST", "/auth/login", csrf=self.token(),
            payload={"username": username, "password": password},
        )


def main() -> None:
    nonce = secrets.token_hex(6)
    fixture = {
        "nonce": nonce,
        "analyst": "ci-analyst-" + nonce,
        "viewer": "ci-viewer-" + nonce,
        "password": secrets.token_urlsafe(32),
    }
    setup = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c", SETUP_FIXTURE],
        input=json.dumps(fixture), text=True, capture_output=True, check=True,
    )
    finding_id = setup.stdout.strip()
    path = "/findings/" + finding_id

    analyst = ApiClient()
    with analyst.opener.open(BASE_URL, timeout=10) as response:
        assert response.status == 200 and b'<div id="root">' in response.read()
    assert analyst.request("GET", "/health/ready")["status"] == "ready"
    analyst.request("GET", "/findings", expected=401)
    analyst.login(fixture["analyst"], fixture["password"])
    assert analyst.request("GET", "/auth/session")["user"]["role"] == "analyst"
    assert analyst.request("GET", path)["title"] == "Synthetic CI finding"

    viewer = ApiClient()
    viewer.login(fixture["viewer"], fixture["password"])
    assert viewer.request("GET", path)["status"] == "new"
    viewer.request(
        "PATCH", path, expected=403, csrf=viewer.token(),
        payload={"status": "investigating", "expected_version": 1},
    )
    viewer.request(
        "POST", path + "/notes", expected=403, csrf=viewer.token(),
        payload={"body": "Synthetic forbidden viewer write."},
    )

    analyst.request(
        "PATCH", path, expected=403,
        payload={"status": "investigating", "expected_version": 1},
    )
    updated = analyst.request(
        "PATCH", path, csrf=analyst.token(),
        payload={"status": "investigating", "expected_version": 1},
    )
    assert updated["version"] == 2
    analyst.request(
        "PATCH", path, expected=409, csrf=analyst.token(),
        payload={"status": "investigating", "expected_version": 1},
    )
    analyst.request(
        "POST", path + "/notes", expected=201, csrf=analyst.token(),
        payload={"body": "Synthetic integration investigation note."},
    )
    assert viewer.request("GET", path + "/notes")["total"] == 1
    events = viewer.request("GET", path + "/history")["items"]
    assert [item["event_type"] for item in events] == [
        "finding.status_changed", "finding.note_added",
    ]
    analyst.request("POST", "/auth/logout", expected=204, csrf=analyst.token())
    analyst.request("GET", "/auth/session", expected=401)
    print("Compose smoke passed: UI/proxy, PostgreSQL, sessions, CSRF, roles, notes, and audit.")


if __name__ == "__main__":
    main()

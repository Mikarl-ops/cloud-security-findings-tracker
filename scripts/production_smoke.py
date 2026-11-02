"""Verify the production images through a local certificate-verified HTTPS edge."""

from __future__ import annotations

import os
import re
import ssl
import subprocess
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request

from smoke_test import ApiClient
from smoke_test import main as workflow_smoke

BASE_URL = "https://localhost:8443"


def main() -> None:
    if os.environ.get("COMPOSE_FILE") != "docker-compose.production-test.yml":
        raise SystemExit("Select the disposable production-test Compose file.")
    ca_path = Path(os.environ["TEST_TLS_DIR"]) / "ca.crt"
    context = ssl.create_default_context(cafile=str(ca_path))
    try:
        with ApiClient(BASE_URL).opener.open(BASE_URL, timeout=10):
            pass
    except URLError as error:
        assert isinstance(error.reason, ssl.SSLCertVerificationError)
    else:
        raise AssertionError("The temporary CA must not be trusted implicitly.")

    client = ApiClient(BASE_URL, context)
    with client.opener.open(BASE_URL, timeout=10) as response:
        html = response.read().decode()
        headers = response.headers
        assert response.status == 200
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Referrer-Policy"] == "no-referrer"
        assert "max-age=" in headers["Strict-Transport-Security"]
        policy = headers["Content-Security-Policy"]
        assert "script-src 'self'" in policy and "frame-ancestors 'none'" in policy
        assert "'unsafe-inline'" not in policy and "'unsafe-eval'" not in policy
        assert headers["Cache-Control"] == "no-store"
        assert "/src/" not in html
    assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', html)
    assert assets and any(path.endswith(".js") for path in assets)
    for path in assets:
        with client.opener.open(BASE_URL + path, timeout=10) as response:
            assert response.status == 200
            assert "immutable" in response.headers["Cache-Control"]
    for path in ("/src/main.tsx", "/node_modules/vite/package.json", "/.env"):
        try:
            client.opener.open(BASE_URL + path, timeout=10)
        except HTTPError as error:
            assert error.code == 404
            assert error.headers["Cache-Control"] == "no-store"
        else:
            raise AssertionError("Development files must not be served.")

    try:
        client.opener.open(
            Request(BASE_URL, headers={"Host": "untrusted.example.invalid"}), timeout=10
        )
    except HTTPError as error:
        assert error.code == 421
    else:
        raise AssertionError("An untrusted Host was accepted.")

    client.token()
    assert list(client.cookies) and all(cookie.secure for cookie in client.cookies)
    cleartext = Request("http://localhost:8443/api/v1/auth/session")
    client.cookies.add_cookie_header(cleartext)
    assert not cleartext.has_header("Cookie")
    workflow_smoke(base_url=BASE_URL, tls_context=context, fixture_service="admin")
    subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "/test/assert_runtime.py"],
        check=True,
    )
    print("Production HTTPS smoke passed: TLS trust, cookies, CSP/headers, immutable assets, "
          "host rejection, authenticated workflows, DB permissions, and runtime restrictions.")


if __name__ == "__main__":
    main()

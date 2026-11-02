"""Verify the reviewed public CA snapshot without network access."""

import hashlib
import ssl
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    certificate = ROOT / "backend/certs/rds-global-bundle.pem"
    expected = (certificate.parent / "rds-global-bundle.sha256").read_text(
        encoding="utf-8-sig"
    ).split()[0]
    content = certificate.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise SystemExit("The public CA snapshot does not match its reviewed checksum.")
    if b"PRIVATE KEY" in content:
        raise SystemExit("Private-key material must never be committed.")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=str(certificate))
    certificates = context.get_ca_certs()
    if not certificates or any(
        ssl.cert_time_to_seconds(item["notAfter"]) < time.time() + 90 * 24 * 60 * 60
        for item in certificates
    ):
        raise SystemExit("Review the public CA snapshot: a CA expires within 90 days.")
    print(f"Public CA snapshot verified: checksum, {len(certificates)} CAs, and expiry horizon.")


if __name__ == "__main__":
    main()

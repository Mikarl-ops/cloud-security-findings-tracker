"""Create ephemeral TLS material and random credentials for a disposable local test only."""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)

    def openssl(*arguments: str) -> None:
        subprocess.run(
            ["openssl", *arguments], cwd=directory, check=True, capture_output=True
        )

    openssl(
        "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
        "-keyout", "ca.key", "-out", "ca.crt", "-subj", "/CN=Synthetic local test CA",
        "-addext", "basicConstraints=critical,CA:TRUE",
    )
    openssl(
        "req", "-newkey", "rsa:2048", "-nodes", "-keyout", "server.key",
        "-out", "server.csr", "-subj", "/CN=localhost",
    )
    (directory / "extensions.cnf").write_text(
        "subjectAltName=DNS:localhost,DNS:db,IP:127.0.0.1\n"
        "basicConstraints=critical,CA:FALSE\nextendedKeyUsage=serverAuth\n",
        encoding="ascii",
    )
    openssl(
        "x509", "-req", "-in", "server.csr", "-CA", "ca.crt", "-CAkey", "ca.key",
        "-CAcreateserial", "-out", "server.crt", "-days", "1",
        "-extfile", "extensions.cnf",
    )
    # File-only bind mounts allow non-root containers to read this ephemeral key.
    # The host directory remains private (0700); the CA private key is never mounted.
    (directory / "server.key").chmod(0o644)
    values = {
        "TEST_TLS_DIR": directory.as_posix(),
        "PRODUCTION_DB_PASSWORD": secrets.token_hex(32),
        "RUNTIME_DB_PASSWORD": secrets.token_hex(32),
        "PRODUCTION_SECRET_KEY": secrets.token_hex(32),
    }
    github_env = os.environ.get("GITHUB_ENV")
    output = Path(github_env) if github_env else directory / "compose.env"
    if github_env:
        for name, value in values.items():
            if name != "TEST_TLS_DIR":
                print("::add-mask::" + value)
    with output.open("a", encoding="utf-8") as stream:
        for name, value in values.items():
            stream.write(f"{name}={value}\n")
    if not github_env:
        output.chmod(0o600)
    print("Disposable TLS and credentials prepared; private keys and values stay outside Git.")


if __name__ == "__main__":
    main()

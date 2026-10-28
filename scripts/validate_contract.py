from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PATHS = {
    "/health/live",
    "/health/ready",
    "/auth/csrf",
    "/auth/login",
    "/auth/session",
    "/auth/logout",
    "/findings/summary",
    "/findings",
    "/findings/{findingId}",
    "/findings/{findingId}/notes",
    "/findings/{findingId}/history",
}
REQUIRED_DOCS = [
    "README.md",
    "docs/architecture.md",
    "docs/threat-model.md",
    "docs/api-contract.md",
    "docs/data-model.md",
    "docs/development.md",
    "docs/decisions/0001-architecture.md",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            fail(f"missing required document: {relative}")

    try:
        spec = json.loads((ROOT / "docs/openapi.json").read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"OpenAPI document is not valid JSON: {error}")

    if spec.get("openapi") != "3.1.0":
        fail("OpenAPI version must be 3.1.0")

    paths = spec.get("paths", {})
    missing = EXPECTED_PATHS - paths.keys()
    if missing:
        fail(f"OpenAPI paths missing from the contract: {', '.join(sorted(missing))}")

    schemas = spec.get("components", {}).get("schemas", {})
    expected_enums = {
        "Role": {"analyst", "viewer"},
        "FindingStatus": {"new", "investigating", "resolved", "dismissed"},
        "Severity": {"critical", "high", "medium", "low", "informational"},
    }
    for schema_name, expected_values in expected_enums.items():
        actual_values = set(schemas.get(schema_name, {}).get("enum", []))
        if actual_values != expected_values:
            fail(f"{schema_name} enum does not match the agreed data model")

    if not {"type", "title", "status"} <= set(schemas.get("Problem", {}).get("required", [])):
        fail("Problem schema is missing RFC 9457 required members")

    if not paths["/health/live"].get("get"):
        fail("liveness operation is missing")
    if paths["/health/live"]["get"].get("security"):
        fail("liveness endpoint must remain public")
    if not paths["/findings"]["get"].get("security"):
        fail("findings endpoint must require a session")

    summary_responses = paths["/findings/summary"]["get"].get("responses", {})
    if "401" not in summary_responses or "$ref" not in summary_responses["401"]:
        fail("findings summary must document authentication failure as a sibling response")
    for path, operations in paths.items():
        for method, operation in operations.items():
            if method not in {"get", "post", "patch", "put", "delete"}:
                continue
            responses = operation.get("responses", {})
            if "200" in responses and any(key.isdigit() for key in responses["200"]):
                fail(f"malformed nested response under {method.upper()} {path}")

    local_link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    ignored_dirs = {".git", ".venv", "venv", "node_modules", "dist"}
    for markdown in ROOT.rglob("*.md"):
        if ignored_dirs.intersection(markdown.parts):
            continue
        for target in local_link.findall(markdown.read_text(encoding="utf-8-sig")):
            if target.startswith(("https://", "http://", "#", "mailto:")):
                continue
            local_target = target.split("#", 1)[0]
            if local_target and not (markdown.parent / local_target).resolve().exists():
                fail(f"broken local link in {markdown.relative_to(ROOT)}: {target}")

    if (ROOT / ".env").exists():
        fail("a local .env file must not be present in the project tree")
    terraform_files = list((ROOT / "infra/terraform").glob("*.tf"))
    if terraform_files:
        fail("Terraform implementation is out of scope for Milestone 1")

    print("Validated OpenAPI routes, role and enum definitions, local documentation links, and Milestone 1 boundaries.")


if __name__ == "__main__":
    main()


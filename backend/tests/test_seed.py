"""Synthetic development-data command coverage."""

from sqlalchemy import select

from tracker.extensions import db
from tracker.models import Finding


def test_seed_demo_is_idempotent_and_preserves_existing_findings(app):
    runner = app.test_cli_runner()

    first = runner.invoke(args=["seed-demo"])
    assert first.exit_code == 0, first.output
    assert "6 added, 0 already present" in first.output

    second = runner.invoke(args=["seed-demo"])
    assert second.exit_code == 0, second.output
    assert "0 added, 6 already present" in second.output

    with app.app_context():
        findings = db.session.scalars(select(Finding)).all()
        assert len(findings) == 7  # The isolated test fixture plus six demo records.
        assert sum(item.source_event_id == "synthetic-test-event" for item in findings) == 1

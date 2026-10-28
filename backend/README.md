# Backend

The Flask application is intentionally only a health-check shell in Milestone 1. Authentication, database access, migrations, findings, notes, and audit operations are specified in the docs directory and arrive in later milestones.

Create and activate a Python 3.12 virtual environment, then install the pinned dependencies from `requirements.lock` and this package with `python -m pip install --no-deps --no-build-isolation -e .`. Run the shell with `flask --app tracker:create_app run`. Run tests with `python -m pytest`.


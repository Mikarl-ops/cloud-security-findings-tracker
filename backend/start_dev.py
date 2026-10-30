"""Run migrations and synthetic seed data before the local Flask development server."""

import os
import subprocess
import sys

FLASK = [sys.executable, "-m", "flask", "--app", "tracker:create_app"]

for command in (FLASK + ["db", "upgrade"], FLASK + ["seed-demo"]):
    subprocess.run(command, check=True)

os.execv(sys.executable, FLASK + ["run", "--no-reload", "--host", "0.0.0.0", "--port", "5000"])

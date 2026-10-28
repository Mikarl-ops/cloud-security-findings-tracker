from flask import Flask, jsonify


def create_app() -> Flask:
    """Create the minimal API shell used during Milestone 1."""
    app = Flask(__name__)

    @app.get("/api/v1/health/live")
    def liveness():
        return jsonify(status="ok")

    return app


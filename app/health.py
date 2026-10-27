"""GET /health: a small JSON status used by Docker and Kubernetes probes."""
import sqlite3

from flask import Blueprint, current_app, jsonify

from .db import get_db

bp = Blueprint("health", __name__)


@bp.route("/health")
def health():
    body = {
        "status": "ok",
        "version": current_app.config["APP_VERSION"],
        "database": "ok",
    }
    try:
        # Reading the products table proves the file exists and the schema is there.
        get_db().execute("SELECT COUNT(*) FROM products").fetchone()
    except sqlite3.Error:
        current_app.logger.exception("Health check failed: database unavailable")
        body.update(status="error", database="unavailable")
        return jsonify(body), 503
    return jsonify(body), 200

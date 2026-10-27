"""Product Catalog application factory."""
import os
import sqlite3

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException

from . import dashboard, db, health, routes, security

APP_VERSION = "v3"
DEFAULT_LOW_STOCK_THRESHOLD = 10


def parse_low_stock_threshold(value):
    """Turn the LOW_STOCK_THRESHOLD setting into a whole number of at least 1.

    A product is "low stock" when its quantity is below this number.
    Invalid values stop the app from starting, so a typo in the setting
    is noticed straight away instead of silently using the wrong number.
    """
    try:
        threshold = int(str(value).strip())
    except ValueError:
        raise ValueError(
            f"LOW_STOCK_THRESHOLD must be a whole number, got {value!r}"
        ) from None
    if threshold < 1:
        raise ValueError(f"LOW_STOCK_THRESHOLD must be at least 1, got {threshold}")
    return threshold


def create_app(test_config=None):
    """Create and configure the Flask app.

    test_config lets tests point the app at a temporary database.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        APP_VERSION=APP_VERSION,
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.environ.get(
            "DATABASE_PATH", os.path.join(app.instance_path, "products.db")
        ),
        LOW_STOCK_THRESHOLD=os.environ.get(
            "LOW_STOCK_THRESHOLD", DEFAULT_LOW_STOCK_THRESHOLD
        ),
    )
    if test_config:
        app.config.update(test_config)
    app.config["LOW_STOCK_THRESHOLD"] = parse_low_stock_threshold(
        app.config["LOW_STOCK_THRESHOLD"]
    )

    # Make sure the folder that holds the SQLite file exists.
    os.makedirs(os.path.dirname(os.path.abspath(app.config["DATABASE"])), exist_ok=True)

    db.init_app(app)
    security.init_app(app)
    app.register_blueprint(routes.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(health.bp)

    @app.context_processor
    def inject_globals():
        return {
            "app_version": app.config["APP_VERSION"],
            "low_stock_threshold": app.config["LOW_STOCK_THRESHOLD"],
        }

    # One friendly page for 400, 404, 405, 500 and other HTTP errors.
    # Unexpected exceptions arrive here as a 500 after Flask logs them.
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return (
            render_template(
                "error.html",
                code=error.code,
                name=error.name,
                description=error.description,
            ),
            error.code,
        )

    # The database file is missing, locked or unreadable: say so plainly
    # instead of showing a generic 500.
    @app.errorhandler(sqlite3.Error)
    def handle_database_error(error):
        app.logger.exception("Database error")
        return (
            render_template(
                "error.html",
                code=503,
                name="Database Unavailable",
                description=(
                    "The product database could not be reached. "
                    "Please try again in a moment."
                ),
            ),
            503,
        )

    return app

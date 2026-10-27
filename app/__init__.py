"""Product Catalog application factory."""
import os

from flask import Flask

from . import db, routes

APP_VERSION = "v1"


def create_app(test_config=None):
    """Create and configure the Flask app.

    test_config lets tests point the app at a temporary database.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.environ.get(
            "DATABASE_PATH", os.path.join(app.instance_path, "products.db")
        ),
    )
    if test_config:
        app.config.update(test_config)

    # Make sure the folder that holds the SQLite file exists.
    os.makedirs(os.path.dirname(os.path.abspath(app.config["DATABASE"])), exist_ok=True)

    db.init_app(app)
    app.register_blueprint(routes.bp)

    @app.context_processor
    def inject_version():
        return {"app_version": APP_VERSION}

    return app

"""SQLite helpers: one connection per request, closed automatically."""
import sqlite3

from flask import current_app, g

# COLLATE NOCASE makes "p001" and "P001" count as the same product ID.
SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY COLLATE NOCASE,
    name       TEXT    NOT NULL,
    price      REAL    NOT NULL CHECK (price >= 0),
    quantity   INTEGER NOT NULL CHECK (quantity >= 0),
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _casefold(value):
    return value.casefold() if isinstance(value, str) else value


def get_db():
    """Return the database connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row  # access columns by name
        # SQLite's LIKE only ignores case for A-Z; casefold() handles any
        # language, so "ÉCLAIR" matches "éclair".
        g.db.create_function("casefold", 1, _casefold, deterministic=True)
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()

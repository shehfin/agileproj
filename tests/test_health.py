"""v3: GET /health and database error handling."""
import os
import sqlite3

import pytest

from app import create_app


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"status": "ok", "version": "v3", "database": "ok"}


def test_health_works_with_products(client, add_product):
    add_product()
    assert client.get("/health").status_code == 200


def test_health_head_request(client):
    assert client.head("/health").status_code == 200


def test_health_rejects_post(client):
    assert client.post("/health").status_code in (400, 405)


def test_health_reports_missing_database(tmp_path):
    db_file = tmp_path / "gone.db"
    app = create_app(
        {"TESTING": True, "DATABASE": str(db_file), "SECRET_KEY": "test", "LOW_STOCK_THRESHOLD": 10}
    )
    os.remove(db_file)  # SQLite recreates an empty file with no products table

    response = app.test_client().get("/health")
    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "error"
    assert body["database"] == "unavailable"
    assert "no such table" not in response.get_data(as_text=True)  # no internals leaked


def test_health_reports_unreachable_database(client, monkeypatch):
    def broken_db():
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr("app.health.get_db", broken_db)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["database"] == "unavailable"


# ---------- Friendly database error page ----------

@pytest.mark.parametrize("url", ["/", "/dashboard"])
def test_pages_show_friendly_error_when_database_fails(client, monkeypatch, url):
    def broken_db():
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr("app.routes.get_db", broken_db)
    monkeypatch.setattr("app.dashboard.get_db", broken_db)
    response = client.get(url)
    assert response.status_code == 503
    html = response.get_data(as_text=True)
    assert "Database Unavailable" in html
    assert "database is locked" not in html  # no internals leaked
    assert "Back to products" in html

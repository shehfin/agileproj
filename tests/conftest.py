import pytest

from app import create_app

CSRF_TOKEN = "test-csrf-token"


@pytest.fixture
def db_path(tmp_path):
    """A fresh SQLite file for each test."""
    return str(tmp_path / "test.db")


@pytest.fixture
def app(db_path):
    return create_app({"TESTING": True, "DATABASE": db_path, "SECRET_KEY": "test"})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def post(client):
    """POST a form with a valid CSRF token, like a real browser would."""

    def _post(url, data=None, follow_redirects=False):
        with client.session_transaction() as session:
            session["csrf_token"] = CSRF_TOKEN
        payload = {"csrf_token": CSRF_TOKEN, **(data or {})}
        return client.post(url, data=payload, follow_redirects=follow_redirects)

    return _post


@pytest.fixture
def add_product(post):
    """Post the add-product form; any field can be overridden."""

    def _add(follow_redirects=True, **fields):
        data = {
            "product_id": "P001",
            "name": "Wireless Mouse",
            "price": "19.99",
            "quantity": "25",
        }
        data.update(fields)
        return post("/products/add", data, follow_redirects=follow_redirects)

    return _add


@pytest.fixture
def get_product(db_path):
    """Read one product straight from the database (None if missing)."""
    import sqlite3

    def _get(product_id):
        with sqlite3.connect(db_path) as conn:
            return conn.execute(
                "SELECT product_id, name, price, quantity FROM products "
                "WHERE product_id = ?",
                (product_id,),
            ).fetchone()

    return _get

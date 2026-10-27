import pytest

from app import create_app


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
def add_product(client):
    """Post the add-product form; any field can be overridden."""

    def _add(follow_redirects=True, **fields):
        data = {
            "product_id": "P001",
            "name": "Wireless Mouse",
            "price": "19.99",
            "quantity": "25",
        }
        data.update(fields)
        return client.post("/products/add", data=data, follow_redirects=follow_redirects)

    return _add

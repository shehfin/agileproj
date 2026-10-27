"""v2: editing and deleting products."""
import sqlite3

import pytest

from app import create_app


def count_products(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]


def edit(post, product_id, follow_redirects=True, **fields):
    data = {"product_id": product_id, "name": "Wireless Mouse", "price": "19.99", "quantity": "25"}
    data.update(fields)
    return post(f"/products/{product_id}/edit", data, follow_redirects=follow_redirects)


@pytest.fixture
def two_products(add_product):
    add_product(product_id="P001", name="Wireless Mouse", price="19.99", quantity="25")
    add_product(product_id="P002", name="Mechanical Keyboard", price="49.50", quantity="10")


# ---------- List page controls ----------

def test_list_has_edit_and_delete_controls(client, two_products):
    html = client.get("/").get_data(as_text=True)
    assert 'href="/products/P001/edit"' in html
    assert 'action="/products/P002/delete"' in html
    assert 'name="csrf_token"' in html


# ---------- Edit ----------

def test_edit_page_is_prefilled(client, two_products):
    response = client.get("/products/P002/edit")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Edit Product" in html
    assert 'value="P002"' in html
    assert 'value="Mechanical Keyboard"' in html
    assert 'value="49.50"' in html
    assert 'value="10"' in html


def test_edit_updates_product(post, two_products, get_product):
    response = post(
        "/products/P001/edit",
        {"product_id": "P001", "name": "Silent Mouse", "price": "21.5", "quantity": "30"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"was updated successfully" in response.data
    assert get_product("P001") == ("P001", "Silent Mouse", 21.5, 30)
    assert get_product("P002") == ("P002", "Mechanical Keyboard", 49.5, 10)  # untouched


def test_edit_redirects_to_list(post, two_products):
    response = post(
        "/products/P001/edit",
        {"product_id": "P001", "name": "Mouse", "price": "1", "quantity": "1"},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_edit_can_change_product_id(post, two_products, get_product, db_path):
    post(
        "/products/P001/edit",
        {"product_id": "M100", "name": "Wireless Mouse", "price": "19.99", "quantity": "25"},
    )
    assert get_product("P001") is None
    assert get_product("M100") == ("M100", "Wireless Mouse", 19.99, 25)
    assert count_products(db_path) == 2


def test_edit_to_existing_id_is_rejected(post, two_products, get_product):
    response = post(
        "/products/P001/edit",
        {"product_id": "P002", "name": "Changed", "price": "1", "quantity": "1"},
    )
    assert response.status_code == 400
    assert b"already exists" in response.data
    assert get_product("P001") == ("P001", "Wireless Mouse", 19.99, 25)
    assert get_product("P002") == ("P002", "Mechanical Keyboard", 49.5, 10)


def test_edit_to_existing_id_different_case_is_rejected(post, two_products, get_product):
    response = post(
        "/products/P001/edit",
        {"product_id": "p002", "name": "Changed", "price": "1", "quantity": "1"},
    )
    assert response.status_code == 400
    assert b"already exists" in response.data
    assert get_product("P001")[1] == "Wireless Mouse"


def test_edit_can_change_case_of_own_id(post, two_products, get_product):
    response = post(
        "/products/P001/edit",
        {"product_id": "p001", "name": "Wireless Mouse", "price": "19.99", "quantity": "25"},
    )
    assert response.status_code == 302
    assert get_product("p001")[0] == "p001"


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("name", "   ", "Product name cannot be blank"),
        ("price", "-2", "Price cannot be negative"),
        ("price", "abc", "Price must be a number"),
        ("quantity", "1.5", "whole number of 0 or more"),
        ("product_id", "P 001", "letters, numbers, hyphens"),
    ],
)
def test_edit_with_invalid_input_is_rejected(post, two_products, get_product, field, value, message):
    data = {"product_id": "P001", "name": "Wireless Mouse", "price": "19.99", "quantity": "25"}
    data[field] = value
    response = post("/products/P001/edit", data)
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert message in html
    assert "Changes were not saved" in html
    assert get_product("P001") == ("P001", "Wireless Mouse", 19.99, 25)


def test_edit_form_keeps_entered_values_after_error(post, two_products):
    html = post(
        "/products/P001/edit",
        {"product_id": "P001", "name": "New Name", "price": "-5", "quantity": "3"},
    ).get_data(as_text=True)
    assert 'value="New Name"' in html
    assert 'value="-5"' in html


def test_edit_missing_product_returns_404(client, post):
    assert client.get("/products/NOPE/edit").status_code == 404
    response = post(
        "/products/NOPE/edit",
        {"product_id": "NOPE", "name": "X", "price": "1", "quantity": "1"},
    )
    assert response.status_code == 404
    assert b"was not found" in response.data


def test_edit_persists_across_app_restarts(post, two_products, db_path):
    post(
        "/products/P002/edit",
        {"product_id": "P002", "name": "Edited Keyboard", "price": "55", "quantity": "2"},
    )
    restarted = create_app({"TESTING": True, "DATABASE": db_path, "SECRET_KEY": "test"})
    html = restarted.test_client().get("/").get_data(as_text=True)
    assert "Edited Keyboard" in html
    assert "Mechanical Keyboard" not in html


# ---------- Delete ----------

def test_delete_removes_product(post, two_products, get_product, db_path):
    response = post("/products/P001/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"was deleted" in response.data
    assert get_product("P001") is None
    assert get_product("P002") is not None
    assert count_products(db_path) == 1


def test_deleted_product_not_listed_or_found(client, post, two_products):
    post("/products/P001/delete")
    # Check the table row, not the page text: the "was deleted" message names it.
    html = client.get("/").get_data(as_text=True)
    assert "<code>P001</code>" not in html
    assert "<code>P002</code>" in html
    assert "No products match" in client.get("/search?q=mouse").get_data(as_text=True)


def test_deleted_id_can_be_reused(post, add_product, two_products, get_product):
    post("/products/P001/delete")
    response = add_product(product_id="P001", name="Replacement")
    assert b"was added successfully" in response.data
    assert get_product("P001")[1] == "Replacement"


def test_delete_missing_product_returns_404(post, db_path, two_products):
    response = post("/products/NOPE/delete")
    assert response.status_code == 404
    assert count_products(db_path) == 2


def test_delete_requires_post(client, two_products, get_product):
    response = client.get("/products/P001/delete")
    assert response.status_code == 405
    assert get_product("P001") is not None


def test_delete_persists_across_app_restarts(post, two_products, db_path):
    post("/products/P002/delete")
    restarted = create_app({"TESTING": True, "DATABASE": db_path, "SECRET_KEY": "test"})
    html = restarted.test_client().get("/").get_data(as_text=True)
    assert "P002" not in html
    assert "P001" in html


# ---------- Legacy v1 IDs ----------

def test_v1_product_with_slash_in_id_can_be_deleted(client, post, db_path):
    """v1 allowed any characters in IDs; v2 must still manage those rows."""
    client.get("/")  # make sure the schema exists
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO products (product_id, name, price, quantity) VALUES (?, ?, ?, ?)",
            ("A/1", "Legacy Item", 1.0, 1),
        )
    assert client.get("/products/A/1/edit").status_code == 200
    response = post("/products/A/1/delete")
    assert response.status_code == 302
    assert count_products(db_path) == 0

import sqlite3

import pytest

from app import create_app


def count_products(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]


# ---------- Pages ----------

def test_home_page_shows_empty_message(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"No products yet" in response.data


def test_add_page_loads(client):
    response = client.get("/products/add")
    assert response.status_code == 200
    assert b"Add Product" in response.data
    assert b'name="product_id"' in response.data


# ---------- Add product ----------

def test_add_product_success(client, add_product, db_path):
    response = add_product()
    assert response.status_code == 200
    assert b"was added successfully" in response.data
    assert b"P001" in response.data
    assert b"Wireless Mouse" in response.data

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT product_id, name, price, quantity FROM products"
        ).fetchone()
    assert row == ("P001", "Wireless Mouse", 19.99, 25)


def test_add_product_redirects_to_list(add_product):
    response = add_product(follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_add_product_trims_whitespace(add_product, db_path):
    add_product(product_id="  P002 ", name="  Keyboard  ", price=" 5 ", quantity=" 3 ")
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT product_id, name, price, quantity FROM products").fetchone()
    assert row == ("P002", "Keyboard", 5.0, 3)


def test_zero_price_and_quantity_are_allowed(add_product, db_path):
    response = add_product(price="0", quantity="0")
    assert b"was added successfully" in response.data
    assert count_products(db_path) == 1


# ---------- View products ----------

def test_list_shows_all_products_sorted_by_id(client, add_product):
    add_product(product_id="P003", name="Monitor", price="150", quantity="4")
    add_product(product_id="P001", name="Mouse", price="10.5", quantity="20")
    add_product(product_id="P002", name="Keyboard", price="25", quantity="8")

    html = client.get("/").get_data(as_text=True)
    assert "3 products" in html
    assert html.index("P001") < html.index("P002") < html.index("P003")
    assert "10.50" in html  # price shown with two decimals


# ---------- Search ----------

@pytest.fixture
def sample_products(add_product):
    add_product(product_id="P001", name="Wireless Mouse", price="19.99", quantity="25")
    add_product(product_id="P002", name="Mechanical Keyboard", price="49.50", quantity="10")
    add_product(product_id="A100", name="USB Cable", price="4.00", quantity="100")


def test_search_by_exact_id(client, sample_products):
    html = client.get("/search?q=P002").get_data(as_text=True)
    assert "Mechanical Keyboard" in html
    assert "Wireless Mouse" not in html
    assert "1 product matching" in html


def test_search_by_partial_id(client, sample_products):
    html = client.get("/search?q=P00").get_data(as_text=True)
    assert "Wireless Mouse" in html
    assert "Mechanical Keyboard" in html
    assert "USB Cable" not in html


def test_search_by_name_is_case_insensitive(client, sample_products):
    html = client.get("/search?q=keyboard").get_data(as_text=True)
    assert "Mechanical Keyboard" in html
    assert "Wireless Mouse" not in html


def test_search_no_match_shows_helpful_message(client, sample_products):
    response = client.get("/search?q=laptop")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "No products match" in html
    assert "laptop" in html
    assert "<table>" not in html


def test_empty_search_redirects_with_message(client):
    response = client.get("/search?q=++", follow_redirects=True)
    assert response.status_code == 200
    assert b"Enter a product ID or name to search" in response.data


def test_search_treats_wildcards_literally(client, sample_products):
    html = client.get("/search?q=%25").get_data(as_text=True)  # q = "%"
    assert "No products match" in html


def test_search_input_is_not_executed_as_sql(client, sample_products):
    html = client.get("/search", query_string={"q": "' OR '1'='1"}).get_data(as_text=True)
    assert "No products match" in html


# ---------- Invalid input ----------

@pytest.mark.parametrize(
    "field, value, message",
    [
        ("product_id", "", "Product ID is required"),
        ("product_id", "X" * 21, "at most 20 characters"),
        ("name", "", "Product name cannot be blank"),
        ("name", "   ", "Product name cannot be blank"),
        ("price", "", "Price is required"),
        ("price", "abc", "Price must be a number"),
        ("price", "-1", "Price cannot be negative"),
        ("price", "nan", "Price must be a number"),
        ("price", "inf", "Price must be a number"),
        ("quantity", "", "Quantity is required"),
        ("quantity", "-5", "whole number of 0 or more"),
        ("quantity", "2.5", "whole number of 0 or more"),
        ("quantity", "ten", "whole number of 0 or more"),
    ],
)
def test_invalid_input_is_rejected(add_product, db_path, field, value, message):
    response = add_product(**{field: value})
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert message in html
    assert "Product was not saved" in html
    assert count_products(db_path) == 0


def test_form_keeps_entered_values_after_error(add_product):
    html = add_product(name="Desk Lamp", price="-3").get_data(as_text=True)
    assert 'value="Desk Lamp"' in html
    assert 'value="-3"' in html


# ---------- Duplicate IDs ----------

def test_duplicate_product_id_is_rejected(add_product, db_path):
    add_product(product_id="P001", name="Original")
    response = add_product(product_id="P001", name="Copy")
    assert response.status_code == 400
    assert b"already exists" in response.data
    assert count_products(db_path) == 1

    with sqlite3.connect(db_path) as conn:
        name = conn.execute("SELECT name FROM products WHERE product_id = 'P001'").fetchone()[0]
    assert name == "Original"


def test_duplicate_check_ignores_case(add_product, db_path):
    add_product(product_id="P001")
    response = add_product(product_id="p001")
    assert response.status_code == 400
    assert b"already exists" in response.data
    assert count_products(db_path) == 1


# ---------- Persistence ----------

def test_products_persist_across_app_restarts(add_product, db_path):
    add_product(product_id="P900", name="Persistent Product")

    # A brand-new app instance pointing at the same database file.
    restarted = create_app({"TESTING": True, "DATABASE": db_path, "SECRET_KEY": "test"})
    html = restarted.test_client().get("/").get_data(as_text=True)
    assert "P900" in html
    assert "Persistent Product" in html

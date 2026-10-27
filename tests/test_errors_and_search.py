"""v2: CSRF protection, error pages and improved search."""
import sqlite3


def count_products(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]


# ---------- CSRF ----------

def test_add_without_csrf_token_is_rejected(client, db_path):
    response = client.post(
        "/products/add",
        data={"product_id": "P001", "name": "Mouse", "price": "1", "quantity": "1"},
    )
    assert response.status_code == 400
    assert b"security token" in response.data
    assert count_products(db_path) == 0


def test_delete_with_wrong_csrf_token_is_rejected(client, add_product, get_product):
    add_product(product_id="P001")
    with client.session_transaction() as session:
        session["csrf_token"] = "real-token"
    response = client.post("/products/P001/delete", data={"csrf_token": "forged"})
    assert response.status_code == 400
    assert get_product("P001") is not None


def test_forms_include_csrf_token(client, add_product):
    add_product(product_id="P001")
    for url in ("/products/add", "/products/P001/edit", "/"):
        assert b'name="csrf_token"' in client.get(url).data


# ---------- Error pages ----------

def test_unknown_page_shows_friendly_404(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404
    html = response.get_data(as_text=True)
    assert "Not Found" in html
    assert "Back to products" in html


def test_method_not_allowed_shows_friendly_page(client):
    response = client.put("/")
    assert response.status_code == 405
    assert b"Back to products" in response.data


# ---------- Search ----------

def test_name_search_is_case_insensitive_for_any_letters(client, add_product):
    add_product(product_id="F001", name="Éclair Box", price="3", quantity="5")
    add_product(product_id="F002", name="Straße Map", price="2", quantity="5")

    assert "Éclair Box" in client.get("/search?q=éCLAIR").get_data(as_text=True)
    assert "Straße Map" in client.get("/search?q=STRASSE").get_data(as_text=True)


def test_search_by_id_is_case_insensitive(client, add_product):
    add_product(product_id="ABC-9", name="Widget")
    assert "Widget" in client.get("/search?q=abc-9").get_data(as_text=True)


def test_search_underscore_is_literal(client, add_product):
    add_product(product_id="A_1", name="Underscore Item")
    add_product(product_id="AB1", name="Other Item")
    html = client.get("/search?q=A_1").get_data(as_text=True)
    assert "Underscore Item" in html
    assert "Other Item" not in html


def test_search_results_include_edit_and_delete(client, add_product):
    add_product(product_id="P001", name="Wireless Mouse")
    html = client.get("/search?q=mouse").get_data(as_text=True)
    assert 'href="/products/P001/edit"' in html
    assert 'action="/products/P001/delete"' in html

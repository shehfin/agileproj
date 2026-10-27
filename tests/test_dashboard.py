"""v3: dashboard statistics and the low-stock threshold setting."""
import re

import pytest

from app import create_app, parse_low_stock_threshold


def stat(html, name):
    """Read a number shown on the dashboard, e.g. stat(html, "total-quantity")."""
    match = re.search(rf'data-stat="{name}">([^<]*)<', html)
    assert match, f"stat {name!r} not found"
    return match.group(1)


@pytest.fixture
def inventory(add_product):
    # Quantities chosen around the default threshold of 10.
    add_product(product_id="A1", name="Out Item", price="2.00", quantity="0")
    add_product(product_id="A2", name="Few Item", price="1.50", quantity="5")
    add_product(product_id="A3", name="Edge Low", price="10", quantity="9")
    add_product(product_id="A4", name="Edge Ok", price="3.25", quantity="10")
    add_product(product_id="A5", name="Plenty", price="0.99", quantity="1000")


def test_dashboard_page_loads(client):
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_empty_dashboard_shows_zeros_and_message(client):
    html = client.get("/dashboard").get_data(as_text=True)
    assert stat(html, "total-products") == "0"
    assert stat(html, "total-quantity") == "0"
    assert stat(html, "total-value") == "0.00"
    assert stat(html, "low-stock") == "0"
    assert stat(html, "out-of-stock") == "0"
    assert "No products yet" in html


def test_dashboard_totals(client, inventory):
    html = client.get("/dashboard").get_data(as_text=True)
    assert stat(html, "total-products") == "5"
    assert stat(html, "total-quantity") == "1,024"  # 0 + 5 + 9 + 10 + 1000
    # 0*2 + 5*1.5 + 9*10 + 10*3.25 + 1000*0.99 = 1120.00
    assert stat(html, "total-value") == "1,120.00"
    assert stat(html, "low-stock") == "3"      # 0, 5 and 9 are below 10
    assert stat(html, "out-of-stock") == "1"   # only the 0


def test_dashboard_lists_low_stock_products_lowest_first(client, inventory):
    html = client.get("/dashboard").get_data(as_text=True)
    section = html.split("Running low", 1)[1]
    assert section.index("<code>A1</code>") < section.index("<code>A2</code>") < section.index("<code>A3</code>")
    assert "<code>A4</code>" not in section  # exactly at the threshold: not low
    assert "<code>A5</code>" not in section


def test_dashboard_when_nothing_is_low(client, add_product):
    add_product(product_id="B1", quantity="50")
    html = client.get("/dashboard").get_data(as_text=True)
    assert "Nothing is running low" in html


def test_dashboard_links_to_filtered_lists(client, inventory):
    html = client.get("/dashboard").get_data(as_text=True)
    assert 'href="/?stock=low"' in html
    assert 'href="/?stock=out"' in html


def test_dashboard_updates_after_edit_and_delete(client, post, inventory):
    post("/products/A1/edit", {"product_id": "A1", "name": "Out Item", "price": "2", "quantity": "20"})
    post("/products/A5/delete")
    html = client.get("/dashboard").get_data(as_text=True)
    assert stat(html, "total-products") == "4"
    assert stat(html, "total-quantity") == "44"  # 20 + 5 + 9 + 10
    assert stat(html, "low-stock") == "2"
    assert stat(html, "out-of-stock") == "0"


def test_dashboard_totals_persist_across_restart(inventory, db_path):
    restarted = create_app(
        {"TESTING": True, "DATABASE": db_path, "SECRET_KEY": "test", "LOW_STOCK_THRESHOLD": 10}
    )
    html = restarted.test_client().get("/dashboard").get_data(as_text=True)
    assert stat(html, "total-products") == "5"
    assert stat(html, "total-quantity") == "1,024"


def test_more_than_ten_low_items_shows_view_all_link(client, add_product):
    for i in range(12):
        add_product(product_id=f"L{i:02d}", name=f"Low {i}", quantity=str(i % 5))
    html = client.get("/dashboard").get_data(as_text=True)
    section = html.split("Running low", 1)[1]
    assert section.count("<code>L") == 10
    assert "View all 12" in html


# ---------- Configurable threshold ----------

def test_threshold_changes_what_counts_as_low(db_path, add_product, client):
    add_product(product_id="T1", quantity="4")
    add_product(product_id="T2", quantity="7")
    stricter = create_app(
        {"TESTING": True, "DATABASE": db_path, "SECRET_KEY": "test", "LOW_STOCK_THRESHOLD": 5}
    )
    html = stricter.test_client().get("/dashboard").get_data(as_text=True)
    assert stat(html, "low-stock") == "1"  # only 4 is below 5
    assert "fewer than 5 units" in html


def test_threshold_read_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("LOW_STOCK_THRESHOLD", "25")
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "env.db")})
    assert app.config["LOW_STOCK_THRESHOLD"] == 25


def test_threshold_defaults_to_ten(monkeypatch, tmp_path):
    monkeypatch.delenv("LOW_STOCK_THRESHOLD", raising=False)
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "default.db")})
    assert app.config["LOW_STOCK_THRESHOLD"] == 10


@pytest.mark.parametrize("value, expected", [(10, 10), ("3", 3), (" 7 ", 7), ("1", 1)])
def test_parse_threshold_valid(value, expected):
    assert parse_low_stock_threshold(value) == expected


@pytest.mark.parametrize("value", ["abc", "", "2.5", "0", "-1"])
def test_parse_threshold_invalid(value):
    with pytest.raises(ValueError, match="LOW_STOCK_THRESHOLD"):
        parse_low_stock_threshold(value)


def test_invalid_threshold_stops_app_start(monkeypatch, tmp_path):
    monkeypatch.setenv("LOW_STOCK_THRESHOLD", "ten")
    with pytest.raises(ValueError, match="must be a whole number"):
        create_app({"TESTING": True, "DATABASE": str(tmp_path / "bad.db")})

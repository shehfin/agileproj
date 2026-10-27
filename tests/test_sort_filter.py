"""v3: sorting, stock filters and low-stock indicators on the product list."""
import re

import pytest


def listed_ids(html):
    """Product IDs in the order the table shows them."""
    return re.findall(r'<td data-label="Product ID"><code>([^<]+)</code>', html)


def row_for(html, product_id):
    """The HTML of one product's table row."""
    for row in html.split("<tr")[1:]:
        if f"<code>{product_id}</code>" in row:
            return row.split("</tr>")[0]
    raise AssertionError(f"row {product_id} not found")


@pytest.fixture
def products(add_product):
    add_product(product_id="P3", name="cherry", price="5.00", quantity="0")
    add_product(product_id="P1", name="Banana", price="20.00", quantity="50")
    add_product(product_id="P2", name="apple", price="12.50", quantity="7")
    add_product(product_id="P4", name="Date", price="12.50", quantity="10")


# ---------- Sorting ----------

def test_default_sort_is_by_id(client, products):
    assert listed_ids(client.get("/").get_data(as_text=True)) == ["P1", "P2", "P3", "P4"]


@pytest.mark.parametrize(
    "query, expected",
    [
        ("sort=name", ["P2", "P1", "P3", "P4"]),                 # apple, Banana, cherry, Date
        ("sort=name&order=desc", ["P4", "P3", "P1", "P2"]),
        ("sort=price", ["P3", "P2", "P4", "P1"]),                # 5, 12.5 (P2), 12.5 (P4), 20
        # Ties (P2 and P4 both 12.50) always list by product ID ascending.
        ("sort=price&order=desc", ["P1", "P2", "P4", "P3"]),
        ("sort=quantity", ["P3", "P2", "P4", "P1"]),             # 0, 7, 10, 50
        ("sort=quantity&order=desc", ["P1", "P4", "P2", "P3"]),
        ("sort=id&order=desc", ["P4", "P3", "P2", "P1"]),
    ],
)
def test_sorting(client, products, query, expected):
    assert listed_ids(client.get(f"/?{query}").get_data(as_text=True)) == expected


def test_name_sort_ignores_case(client, products):
    # Plain byte order would put "Banana" and "Date" before "apple".
    ids = listed_ids(client.get("/?sort=name").get_data(as_text=True))
    assert ids[0] == "P2"


@pytest.mark.parametrize("query", ["sort=hacker", "sort=price;DROP TABLE products", "order=sideways"])
def test_unknown_sort_values_fall_back_to_default(client, products, query):
    response = client.get(f"/?{query}")
    assert response.status_code == 200
    assert listed_ids(response.get_data(as_text=True)) == ["P1", "P2", "P3", "P4"]


def test_selected_sort_is_shown_in_controls(client, products):
    html = client.get("/?sort=price&order=desc").get_data(as_text=True)
    assert '<option value="price" selected>' in html
    assert '<option value="desc" selected>' in html
    assert "sorted by price, descending" in html


# ---------- Stock filters ----------

def test_filter_low_stock(client, products):
    html = client.get("/?stock=low").get_data(as_text=True)
    assert listed_ids(html) == ["P2", "P3"]  # 7 and 0 are below 10; P4 (10) is not
    assert "low stock" in html


def test_filter_out_of_stock(client, products):
    assert listed_ids(client.get("/?stock=out").get_data(as_text=True)) == ["P3"]


def test_filter_in_stock(client, products):
    assert listed_ids(client.get("/?stock=ok").get_data(as_text=True)) == ["P1", "P4"]


def test_unknown_filter_shows_everything(client, products):
    assert len(listed_ids(client.get("/?stock=bogus").get_data(as_text=True))) == 4


def test_filter_and_sort_combine(client, products):
    ids = listed_ids(client.get("/?stock=low&sort=quantity&order=desc").get_data(as_text=True))
    assert ids == ["P2", "P3"]


def test_search_combines_with_filter_and_sort(client, add_product):
    add_product(product_id="M1", name="Mouse Large", quantity="3")
    add_product(product_id="M2", name="Mouse Small", quantity="1")
    add_product(product_id="M3", name="Mouse Pad", quantity="40")
    add_product(product_id="K1", name="Keyboard", quantity="2")

    for url in ("/search?q=mouse&stock=low&sort=quantity", "/?q=mouse&stock=low&sort=quantity"):
        html = client.get(url).get_data(as_text=True)
        assert listed_ids(html) == ["M2", "M1"]
        assert "matching “mouse”" in html


def test_list_page_search_box_with_blank_query_lists_everything(client, products):
    response = client.get("/?q=++")
    assert response.status_code == 200
    assert len(listed_ids(response.get_data(as_text=True))) == 4


def test_reset_link_only_when_filtered(client, products):
    assert ">Reset<" not in client.get("/").get_data(as_text=True)
    assert ">Reset<" in client.get("/?stock=low").get_data(as_text=True)
    assert ">Reset<" in client.get("/search?q=apple").get_data(as_text=True)


# ---------- Empty states ----------

def test_empty_low_stock_filter_message(client, add_product):
    add_product(product_id="Z1", quantity="99")
    html = client.get("/?stock=low").get_data(as_text=True)
    assert "No products are low on stock" in html
    assert "at least 10 units" in html
    assert "No products yet" not in html


def test_empty_out_of_stock_filter_message(client, add_product):
    add_product(product_id="Z1", quantity="3")
    assert "No products are out of stock" in client.get("/?stock=out").get_data(as_text=True)


def test_search_no_match_mentions_active_filter(client, add_product):
    add_product(product_id="Z1", name="Lamp", quantity="99")
    html = client.get("/search?q=lamp&stock=low").get_data(as_text=True)
    assert "No products match “lamp” with the “Low stock” filter" in html


def test_empty_catalog_message_wins_over_filters(client):
    assert "No products yet" in client.get("/?stock=low").get_data(as_text=True)


# ---------- Low-stock indicators ----------

def test_low_stock_rows_are_highlighted(client, products):
    html = client.get("/").get_data(as_text=True)
    assert 'class="row-out"' in row_for(html, "P3") and "Out of stock" in row_for(html, "P3")
    assert 'class="row-low"' in row_for(html, "P2") and "Low stock" in row_for(html, "P2")
    for ok_id in ("P1", "P4"):  # 50, and exactly 10 (not below the threshold)
        row = row_for(html, ok_id)
        assert "row-low" not in row and "row-out" not in row
        assert "badge" not in row


def test_threshold_is_documented_on_list_page(client):
    assert "Low stock means fewer than 10 units" in client.get("/").get_data(as_text=True)


def test_indicator_follows_configured_threshold(db_path, add_product):
    from app import create_app

    add_product(product_id="Q1", quantity="7")
    app = create_app(
        {"TESTING": True, "DATABASE": db_path, "SECRET_KEY": "test", "LOW_STOCK_THRESHOLD": 5}
    )
    html = app.test_client().get("/").get_data(as_text=True)
    assert "badge" not in row_for(html, "Q1")  # 7 is not below 5

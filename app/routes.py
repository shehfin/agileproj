"""Product routes: list, search, sort/filter, add, edit and delete."""
import sqlite3

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from .db import get_db
from .validation import validate_product

bp = Blueprint("products", __name__)

PRODUCT_COLUMNS = "product_id, name, price, quantity"

# Only these fixed SQL snippets ever reach ORDER BY. User input picks a key;
# it is never placed into the SQL itself.
SORT_OPTIONS = {
    "id": ("Product ID", "product_id"),
    "name": ("Name", "casefold(name)"),
    "price": ("Price", "price"),
    "quantity": ("Quantity", "quantity"),
}
ORDER_OPTIONS = {"asc": "Ascending", "desc": "Descending"}
STOCK_OPTIONS = {
    "all": "All stock levels",
    "low": "Low stock",
    "out": "Out of stock",
    "ok": "In stock (not low)",
}
DEFAULT_LIST_OPTIONS = {"sort": "id", "order": "asc", "stock": "all"}


def _escape_like(text):
    """Make %, _ and \\ match literally inside a LIKE pattern."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _duplicate_message(product_id):
    return f'Product ID "{product_id}" already exists. Choose a different ID.'


def _get_product_or_404(product_id):
    product = get_db().execute(
        f"SELECT {PRODUCT_COLUMNS} FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()
    if product is None:
        abort(404, description=f'Product "{product_id}" was not found. It may have been deleted.')
    return product


def _id_taken(product_id, ignore_id=None):
    """True if another product already uses product_id (case-insensitive).

    ignore_id skips the product being edited, so it can keep its own ID.
    """
    sql = "SELECT 1 FROM products WHERE product_id = ?"
    params = [product_id]
    if ignore_id is not None:
        sql += " AND product_id <> ?"
        params.append(ignore_id)
    return get_db().execute(sql, params).fetchone() is not None


def _price_for_input(price):
    """Show a stored price in the edit form without hiding extra decimals."""
    return f"{price:.2f}" if round(price, 2) == price else str(price)


def _list_options(args):
    """Read sort/order/stock from the URL, falling back to defaults for unknown values."""
    options = {}
    for key, allowed in (("sort", SORT_OPTIONS), ("order", ORDER_OPTIONS), ("stock", STOCK_OPTIONS)):
        value = args.get(key, DEFAULT_LIST_OPTIONS[key])
        options[key] = value if value in allowed else DEFAULT_LIST_OPTIONS[key]
    return options


def _fetch_products(query, options):
    threshold = current_app.config["LOW_STOCK_THRESHOLD"]
    conditions, params = [], []

    if query:
        # Partial, case-insensitive match on ID or name. Values are passed as
        # parameters, never formatted into the SQL string.
        pattern = f"%{_escape_like(query)}%"
        conditions.append(
            "(casefold(product_id) LIKE casefold(?) ESCAPE '\\' "
            "OR casefold(name) LIKE casefold(?) ESCAPE '\\')"
        )
        params += [pattern, pattern]

    if options["stock"] == "low":
        conditions.append("quantity < ?")
        params.append(threshold)
    elif options["stock"] == "out":
        conditions.append("quantity = 0")
    elif options["stock"] == "ok":
        conditions.append("quantity >= ?")
        params.append(threshold)

    sql = f"SELECT {PRODUCT_COLUMNS} FROM products"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    direction = "DESC" if options["order"] == "desc" else "ASC"
    # product_id breaks ties so equal prices/quantities always list in the same order.
    sql += f" ORDER BY {SORT_OPTIONS[options['sort']][1]} {direction}, product_id"
    return get_db().execute(sql, params).fetchall()


def _render_product_list(query):
    options = _list_options(request.args)
    products = _fetch_products(query, options)
    has_any_products = bool(products) or (
        get_db().execute("SELECT 1 FROM products LIMIT 1").fetchone() is not None
    )
    return render_template(
        "index.html",
        products=products,
        query=query,
        options=options,
        is_filtered=options != DEFAULT_LIST_OPTIONS,
        has_any_products=has_any_products,
        sort_options=SORT_OPTIONS,
        order_options=ORDER_OPTIONS,
        stock_options=STOCK_OPTIONS,
    )


@bp.route("/")
def index():
    # The list page's own form sends q here; a blank q simply lists everything.
    query = request.args.get("q", "").strip() or None
    return _render_product_list(query)


@bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        flash("Enter a product ID or name to search.", "error")
        return redirect(url_for("products.index"))
    return _render_product_list(query)


@bp.route("/products/add", methods=["GET", "POST"])
def add_product():
    if request.method == "GET":
        return render_template("product_form.html", mode="add", form={}, errors={})

    data, errors = validate_product(request.form)
    if not errors and _id_taken(data["product_id"]):
        errors["product_id"] = _duplicate_message(data["product_id"])

    if not errors:
        db = get_db()
        try:
            db.execute(
                "INSERT INTO products (product_id, name, price, quantity) "
                "VALUES (?, ?, ?, ?)",
                (data["product_id"], data["name"], data["price"], data["quantity"]),
            )
            db.commit()
        except sqlite3.IntegrityError:
            # Another request saved the same ID between our check and insert.
            errors["product_id"] = _duplicate_message(data["product_id"])
        else:
            flash(f'Product "{data["name"]}" was added successfully.', "success")
            return redirect(url_for("products.index"))

    flash("Product was not saved. Please fix the errors below.", "error")
    return (
        render_template("product_form.html", mode="add", form=request.form, errors=errors),
        400,
    )


# <path:...> so product IDs saved by v1 (which allowed any characters,
# including "/") can still be edited and deleted.
@bp.route("/products/<path:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    product = _get_product_or_404(product_id)

    if request.method == "GET":
        form = {
            "product_id": product["product_id"],
            "name": product["name"],
            "price": _price_for_input(product["price"]),
            "quantity": str(product["quantity"]),
        }
        return render_template(
            "product_form.html", mode="edit", product=product, form=form, errors={}
        )

    data, errors = validate_product(request.form)
    if not errors and _id_taken(data["product_id"], ignore_id=product["product_id"]):
        errors["product_id"] = _duplicate_message(data["product_id"])

    if not errors:
        db = get_db()
        try:
            db.execute(
                "UPDATE products SET product_id = ?, name = ?, price = ?, quantity = ? "
                "WHERE product_id = ?",
                (
                    data["product_id"],
                    data["name"],
                    data["price"],
                    data["quantity"],
                    product["product_id"],
                ),
            )
            db.commit()
        except sqlite3.IntegrityError:
            errors["product_id"] = _duplicate_message(data["product_id"])
        else:
            flash(f'Product "{data["name"]}" was updated successfully.', "success")
            return redirect(url_for("products.index"))

    flash("Changes were not saved. Please fix the errors below.", "error")
    return (
        render_template(
            "product_form.html", mode="edit", product=product, form=request.form, errors=errors
        ),
        400,
    )


@bp.route("/products/<path:product_id>/delete", methods=["POST"])
def delete_product(product_id):
    product = _get_product_or_404(product_id)
    db = get_db()
    db.execute("DELETE FROM products WHERE product_id = ?", (product["product_id"],))
    db.commit()
    flash(
        f'Product "{product["name"]}" ({product["product_id"]}) was deleted.', "success"
    )
    return redirect(url_for("products.index"))

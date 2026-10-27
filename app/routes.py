"""Product routes: list, search and add."""
import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .db import get_db
from .validation import validate_product

bp = Blueprint("products", __name__)

PRODUCT_COLUMNS = "product_id, name, price, quantity"


def _escape_like(text):
    """Make %, _ and \\ match literally inside a LIKE pattern."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@bp.route("/")
def index():
    products = get_db().execute(
        f"SELECT {PRODUCT_COLUMNS} FROM products ORDER BY product_id"
    ).fetchall()
    return render_template("index.html", products=products, query=None)


@bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        flash("Enter a product ID or name to search.", "error")
        return redirect(url_for("products.index"))

    # Partial, case-insensitive match on ID or name. Values are passed as
    # parameters, never formatted into the SQL string.
    pattern = f"%{_escape_like(query)}%"
    products = get_db().execute(
        f"SELECT {PRODUCT_COLUMNS} FROM products "
        "WHERE product_id LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\' "
        "ORDER BY product_id",
        (pattern, pattern),
    ).fetchall()
    return render_template("index.html", products=products, query=query)


@bp.route("/products/add", methods=["GET", "POST"])
def add_product():
    if request.method == "GET":
        return render_template("add.html", form={}, errors={})

    data, errors = validate_product(request.form)
    db = get_db()

    if not errors:
        exists = db.execute(
            "SELECT 1 FROM products WHERE product_id = ?", (data["product_id"],)
        ).fetchone()
        if exists:
            errors["product_id"] = f'Product ID "{data["product_id"]}" already exists.'

    if not errors:
        try:
            db.execute(
                "INSERT INTO products (product_id, name, price, quantity) "
                "VALUES (?, ?, ?, ?)",
                (data["product_id"], data["name"], data["price"], data["quantity"]),
            )
            db.commit()
        except sqlite3.IntegrityError:
            # Another request saved the same ID between our check and insert.
            errors["product_id"] = f'Product ID "{data["product_id"]}" already exists.'
        else:
            flash(f'Product "{data["name"]}" was added successfully.', "success")
            return redirect(url_for("products.index"))

    flash("Product was not saved. Please fix the errors below.", "error")
    return render_template("add.html", form=request.form, errors=errors), 400

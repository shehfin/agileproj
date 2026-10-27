"""Dashboard: inventory totals and the products that are running low."""
from flask import Blueprint, current_app, render_template

from .db import get_db

bp = Blueprint("dashboard", __name__)

LOW_STOCK_LIST_LIMIT = 10


def inventory_stats(threshold):
    """Totals across all products. Low stock means quantity < threshold."""
    row = get_db().execute(
        "SELECT COUNT(*) AS total_products, "
        "       COALESCE(SUM(quantity), 0) AS total_quantity, "
        "       COALESCE(SUM(price * quantity), 0) AS total_value, "
        "       COALESCE(SUM(quantity < ?), 0) AS low_stock, "
        "       COALESCE(SUM(quantity = 0), 0) AS out_of_stock "
        "FROM products",
        (threshold,),
    ).fetchone()
    stats = dict(row)
    stats["total_value"] = round(stats["total_value"], 2)
    return stats


@bp.route("/dashboard")
def dashboard():
    threshold = current_app.config["LOW_STOCK_THRESHOLD"]
    low_stock_products = get_db().execute(
        "SELECT product_id, name, price, quantity FROM products "
        "WHERE quantity < ? ORDER BY quantity, product_id LIMIT ?",
        (threshold, LOW_STOCK_LIST_LIMIT),
    ).fetchall()
    return render_template(
        "dashboard.html",
        stats=inventory_stats(threshold),
        low_stock_products=low_stock_products,
        low_stock_list_limit=LOW_STOCK_LIST_LIMIT,
    )

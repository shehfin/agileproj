"""Server-side validation for product form data."""
import math
import re

PRODUCT_ID_MAX_LENGTH = 20
NAME_MAX_LENGTH = 100

_WHOLE_NUMBER = re.compile(r"^\d+$")


def validate_product(form):
    """Check submitted form values.

    Returns (data, errors): data holds the cleaned values, errors maps a
    field name to a message. An empty errors dict means the input is valid.
    """
    errors = {}
    product_id = form.get("product_id", "").strip()
    name = form.get("name", "").strip()
    price_raw = form.get("price", "").strip()
    quantity_raw = form.get("quantity", "").strip()

    if not product_id:
        errors["product_id"] = "Product ID is required."
    elif len(product_id) > PRODUCT_ID_MAX_LENGTH:
        errors["product_id"] = (
            f"Product ID must be at most {PRODUCT_ID_MAX_LENGTH} characters."
        )

    if not name:
        errors["name"] = "Product name cannot be blank."
    elif len(name) > NAME_MAX_LENGTH:
        errors["name"] = f"Product name must be at most {NAME_MAX_LENGTH} characters."

    price = None
    if not price_raw:
        errors["price"] = "Price is required."
    else:
        try:
            price = float(price_raw)
        except ValueError:
            errors["price"] = "Price must be a number, for example 19.99."
        else:
            if not math.isfinite(price):
                errors["price"] = "Price must be a number, for example 19.99."
            elif price < 0:
                errors["price"] = "Price cannot be negative."
            elif price == 0:
                price = 0.0  # turns -0.0 into 0.0

    quantity = None
    if not quantity_raw:
        errors["quantity"] = "Quantity is required."
    elif not _WHOLE_NUMBER.match(quantity_raw):
        errors["quantity"] = "Quantity must be a whole number of 0 or more."
    else:
        quantity = int(quantity_raw)

    data = {
        "product_id": product_id,
        "name": name,
        "price": price,
        "quantity": quantity,
    }
    return data, errors

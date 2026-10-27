"""Server-side validation for product form data."""
import re

PRODUCT_ID_MAX_LENGTH = 20
NAME_MAX_LENGTH = 100
PRICE_MAX = 1_000_000
QUANTITY_MAX = 1_000_000

# [0-9] rather than \d so only ASCII digits are accepted.
_PRODUCT_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_PRICE = re.compile(r"^[0-9]+(\.[0-9]{1,2})?$")
_PRICE_TOO_PRECISE = re.compile(r"^[0-9]+\.[0-9]{3,}$")
_WHOLE_NUMBER = re.compile(r"^[0-9]+$")


def validate_product(form):
    """Check submitted form values.

    Returns (data, errors): data holds the cleaned values, errors maps a
    field name to a message. An empty errors dict means the input is valid.
    """
    errors = {}
    product_id = form.get("product_id", "").strip()
    # Collapse runs of spaces/tabs inside the name: "Big   Desk" -> "Big Desk".
    name = " ".join(form.get("name", "").split())
    price_raw = form.get("price", "").strip()
    quantity_raw = form.get("quantity", "").strip()

    if not product_id:
        errors["product_id"] = "Product ID is required."
    elif len(product_id) > PRODUCT_ID_MAX_LENGTH:
        errors["product_id"] = (
            f"Product ID must be at most {PRODUCT_ID_MAX_LENGTH} characters."
        )
    elif not _PRODUCT_ID.match(product_id):
        errors["product_id"] = (
            "Product ID can only contain letters, numbers, hyphens (-) "
            "and underscores (_)."
        )

    if not name:
        errors["name"] = "Product name cannot be blank."
    elif len(name) > NAME_MAX_LENGTH:
        errors["name"] = f"Product name must be at most {NAME_MAX_LENGTH} characters."

    price = None
    if not price_raw:
        errors["price"] = "Price is required."
    elif price_raw.startswith("-") and _PRICE.match(price_raw[1:]):
        errors["price"] = "Price cannot be negative."
    elif _PRICE_TOO_PRECISE.match(price_raw):
        errors["price"] = "Price can have at most 2 decimal places."
    elif not _PRICE.match(price_raw):
        errors["price"] = "Price must be a number, for example 19.99."
    else:
        price = float(price_raw)
        if price > PRICE_MAX:
            errors["price"] = f"Price cannot be more than {PRICE_MAX:,}."
            price = None

    quantity = None
    if not quantity_raw:
        errors["quantity"] = "Quantity is required."
    elif not _WHOLE_NUMBER.match(quantity_raw):
        errors["quantity"] = "Quantity must be a whole number of 0 or more."
    else:
        quantity = int(quantity_raw)
        if quantity > QUANTITY_MAX:
            errors["quantity"] = f"Quantity cannot be more than {QUANTITY_MAX:,}."
            quantity = None

    data = {
        "product_id": product_id,
        "name": name,
        "price": price,
        "quantity": quantity,
    }
    return data, errors

"""v2: unit tests for validate_product (no web requests)."""
import pytest

from app.validation import validate_product

VALID = {"product_id": "P001", "name": "Desk", "price": "10", "quantity": "1"}


def validate(**overrides):
    return validate_product({**VALID, **overrides})


@pytest.mark.parametrize("product_id", ["P001", "ab-12_X", "9", "A" * 20])
def test_valid_product_ids(product_id):
    data, errors = validate(product_id=product_id)
    assert errors == {}
    assert data["product_id"] == product_id


@pytest.mark.parametrize("product_id", ["P 001", "P/001", "P001!", "café", "<b>"])
def test_product_id_rejects_special_characters(product_id):
    _, errors = validate(product_id=product_id)
    assert "letters, numbers, hyphens" in errors["product_id"]


def test_name_whitespace_is_collapsed():
    data, errors = validate(name="  Big \t  Oak   Desk  ")
    assert errors == {}
    assert data["name"] == "Big Oak Desk"


def test_name_length_limit():
    assert validate(name="x" * 100)[1] == {}
    assert "at most 100 characters" in validate(name="x" * 101)[1]["name"]


@pytest.mark.parametrize(
    "raw, expected",
    [("0", 0.0), ("19", 19.0), ("19.9", 19.9), ("19.99", 19.99), ("1000000", 1_000_000.0)],
)
def test_valid_prices(raw, expected):
    data, errors = validate(price=raw)
    assert errors == {}
    assert data["price"] == expected


@pytest.mark.parametrize(
    "raw, message",
    [
        ("19.999", "at most 2 decimal places"),
        ("-0.5", "cannot be negative"),
        ("1e3", "must be a number"),
        ("1,000", "must be a number"),
        (".5", "must be a number"),
        ("12.", "must be a number"),
        ("nan", "must be a number"),
        ("1000000.01", "cannot be more than 1,000,000"),
    ],
)
def test_invalid_prices(raw, message):
    data, errors = validate(price=raw)
    assert message in errors["price"]
    assert data["price"] is None


@pytest.mark.parametrize("raw, expected", [("0", 0), ("7", 7), ("1000000", 1_000_000)])
def test_valid_quantities(raw, expected):
    data, errors = validate(quantity=raw)
    assert errors == {}
    assert data["quantity"] == expected


@pytest.mark.parametrize(
    "raw, message",
    [
        ("-1", "whole number of 0 or more"),
        ("+5", "whole number of 0 or more"),
        ("3.0", "whole number of 0 or more"),
        ("١٢", "whole number of 0 or more"),  # non-ASCII digits
        ("1000001", "cannot be more than 1,000,000"),
    ],
)
def test_invalid_quantities(raw, message):
    data, errors = validate(quantity=raw)
    assert message in errors["quantity"]
    assert data["quantity"] is None


def test_all_errors_reported_together():
    _, errors = validate_product({"product_id": "", "name": "", "price": "", "quantity": ""})
    assert set(errors) == {"product_id", "name", "price", "quantity"}


def test_missing_fields_are_treated_as_blank():
    _, errors = validate_product({})
    assert set(errors) == {"product_id", "name", "price", "quantity"}

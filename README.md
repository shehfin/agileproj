# Product Catalog — v2

A small Flask + SQLite product catalog built for a DevOps project (Student ID **24MIS0175**).

## Features

**From v1**

- **Add Product**: product ID, name, price and quantity
- **View Products**: all saved products in a table, sorted by product ID
- **Search Products**: partial, case-insensitive match on product ID or name, with a message when nothing matches

**New in v2**

- **Edit Product**: change any field, including the product ID (still checked for duplicates)
- **Delete Product**: with a confirmation prompt
- **Stricter server-side validation**: see the table below
- **Case-insensitive search for any language**: for example, `ÉCLAIR` finds `éclair` and `STRASSE` finds `Straße`
- **CSRF protection** on every form, so other websites can't submit forms such as Delete through your browser
- **Friendly error pages** for 400, 404, 405 and 500 responses
- **Responsive layout**: on phones, table rows become stacked cards

## Validation rules

| Field | Rule |
|---|---|
| Product ID | Required, unique (case-insensitive), max 20 characters, letters, numbers, `-` and `_` only |
| Name | Cannot be blank, max 100 characters, extra spaces collapsed |
| Price | Number from 0 to 1,000,000 with at most 2 decimal places |
| Quantity | Whole number from 0 to 1,000,000 |

All SQL uses parameterized queries.

## Routes

| Method | URL | Purpose |
|---|---|---|
| GET | `/` | List products |
| GET | `/search?q=` | Search by ID or name |
| GET, POST | `/products/add` | Add a product |
| GET, POST | `/products/<id>/edit` | Edit a product |
| POST | `/products/<id>/delete` | Delete a product |

## Project structure

```
app/
  __init__.py      create_app() factory and error pages
  db.py            SQLite connection and schema
  routes.py        list, search, add, edit and delete routes
  security.py      CSRF token check for POST forms
  validation.py    form validation
  templates/       base, index, product_form (add/edit), error
  static/css/      style.css
  static/js/       app.js (delete confirmation)
tests/             pytest suite
run.py             development server entry point
Dockerfile         container image (gunicorn on port 5000)
```

## Run locally

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python run.py
```

Open http://127.0.0.1:5000. The database is created at `instance/products.db`.

| Environment variable | Purpose |
|---|---|
| `DATABASE_PATH` | Store the database somewhere else |
| `SECRET_KEY` | Signs the session cookie that holds the CSRF token; set a random value outside local development |

A v1 database works with v2 as-is, because the table layout is unchanged.

## Run the tests

```powershell
python -m pytest -v
```

| File | Covers |
|---|---|
| `tests/test_products.py` | v1 behaviour: add, list, search, invalid input, duplicates, persistence |
| `tests/test_edit_delete.py` | Edit and delete, including duplicate IDs, invalid input, 404s and persistence |
| `tests/test_validation.py` | Validation rules, tested directly |
| `tests/test_errors_and_search.py` | CSRF, error pages, and case-insensitive search for any language |

Each test uses its own temporary database, so your real data is never touched.

## Docker

```powershell
docker build -t shehfin/product-catalog:v2 .
docker run -d --name product-catalog-v2 -p 5000:5000 -v product-catalog-v2-data:/app/data shehfin/product-catalog:v2
```

Open http://localhost:5000. The named volume keeps products when the container is recreated.

Stop and remove:

```powershell
docker rm -f product-catalog-v2
```

## Versions

| Branch | Scope |
|---|---|
| `v1` | Add, view and search products |
| `v2` | v1 + edit, delete, improved validation and UI |
| `v3` | v2 + dashboard statistics, sorting, filtering, low-stock indicators, health endpoint |

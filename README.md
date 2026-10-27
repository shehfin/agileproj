# Product Catalog — v1

A small Flask + SQLite product catalog built for a DevOps project (Student ID **24MIS0175**).

## Features (v1)

- **Add Product** — product ID, name, price and quantity
- **View Products** — all saved products in a table, sorted by product ID
- **Search Products** — partial, case-insensitive match on product ID or name, with a message when nothing matches

Validation happens on the server:

| Field | Rule |
|---|---|
| Product ID | Required, unique (case-insensitive), max 20 characters |
| Name | Cannot be blank, max 100 characters |
| Price | Number, 0 or more |
| Quantity | Whole number, 0 or more |

All SQL uses parameterized queries.

## Project structure

```
app/
  __init__.py      create_app() factory
  db.py            SQLite connection and schema
  routes.py        list, search and add routes
  validation.py    form validation
  templates/       base.html, index.html, add.html
  static/css/      style.css
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

Set `DATABASE_PATH` to store the database somewhere else.

## Run the tests

```powershell
python -m pytest -v
```

Each test uses its own temporary database, so your real data is never touched.

## Docker

```powershell
docker build -t shehfin/product-catalog:v1 .
docker run -d --name product-catalog-v1 -p 5000:5000 -v product-catalog-v1-data:/app/data shehfin/product-catalog:v1
```

Open http://localhost:5000. The named volume keeps products when the container is recreated.

Stop and remove:

```powershell
docker rm -f product-catalog-v1
```

## Versions

| Branch | Scope |
|---|---|
| `v1` | Add, view and search products |
| `v2` | v1 + edit, delete, improved validation and UI |
| `v3` | v2 + dashboard statistics, sorting, filtering, low-stock indicators, health endpoint |

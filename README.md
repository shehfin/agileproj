# Product Catalog — v3

A small Flask + SQLite product catalog built for a DevOps project (Student ID **24MIS0175**).

## Features

**From v1**

- **Add Product**: product ID, name, price and quantity
- **View Products**: all saved products in a table
- **Search Products**: partial, case-insensitive match on product ID or name

**From v2**

- **Edit and Delete Products**: delete asks for confirmation
- **Strict server-side validation**, **CSRF protection** and **friendly error pages**
- **Responsive layout**: on phones, table rows become stacked cards

**New in v3**

- **Dashboard** (`/dashboard`):
  - total products
  - total quantity
  - inventory value (sum of price × quantity)
  - low-stock and out-of-stock counts
  - a "Running low" list of up to 10 products, lowest quantity first
- **Sorting**: by product ID, name (case-insensitive), price or quantity, ascending or descending. When values tie, products are listed by product ID.
- **Stock filters**: all, low stock, out of stock, or in stock (not low). These combine with search and sorting.
- **Low-stock indicators**: rows are highlighted and badged.
  - Amber **Low stock**: quantity is below the threshold
  - Red **Out of stock**: quantity is 0
- **Health endpoint** (`GET /health`): returns JSON and checks that the database can be read
- **Database errors**: show a friendly 503 page instead of a crash
- **Clearer empty states**: separate messages for an empty catalog, a search with no matches, and a filter with no results

## Low-stock threshold

| Setting | `LOW_STOCK_THRESHOLD` environment variable |
|---|---|
| Default | `10` |
| Rule | A product is **low stock** when `quantity < LOW_STOCK_THRESHOLD`. With the default, 9 is low and 10 is not. |
| Allowed values | Whole number, 1 or more |
| Invalid value | The app refuses to start and logs `ValueError: LOW_STOCK_THRESHOLD must be ...` |

The current threshold is shown on the Products and Dashboard pages.

## Health endpoint

```
GET /health
```

| Situation | Status | Body |
|---|---|---|
| Healthy | `200` | `{"status": "ok", "version": "v3", "database": "ok"}` |
| Database unreadable | `503` | `{"status": "error", "version": "v3", "database": "unavailable"}` |

Error details are logged but never included in the response. The Docker image uses this endpoint as its `HEALTHCHECK`.

## Routes

| Method | URL | Purpose |
|---|---|---|
| GET | `/` | List products. Optional query parameters: `q`, `sort` (`id`, `name`, `price`, `quantity`), `order` (`asc`, `desc`), `stock` (`all`, `low`, `out`, `ok`) |
| GET | `/search?q=` | Search; accepts the same `sort`, `order` and `stock` parameters |
| GET | `/dashboard` | Inventory statistics |
| GET, POST | `/products/add` | Add a product |
| GET, POST | `/products/<id>/edit` | Edit a product |
| POST | `/products/<id>/delete` | Delete a product |
| GET | `/health` | Health check (JSON) |

Unknown `sort`, `order` or `stock` values fall back to the defaults. Only fixed, built-in column names ever reach `ORDER BY`.

## Validation rules

| Field | Rule |
|---|---|
| Product ID | Required, unique (case-insensitive), max 20 characters, letters, numbers, `-` and `_` only |
| Name | Cannot be blank, max 100 characters, extra spaces collapsed |
| Price | Number from 0 to 1,000,000 with at most 2 decimal places |
| Quantity | Whole number from 0 to 1,000,000 |

All SQL uses parameterized queries.

## Project structure

```
app/
  __init__.py      create_app() factory, settings, error pages
  db.py            SQLite connection and schema
  routes.py        list/search/sort/filter, add, edit, delete
  dashboard.py     dashboard statistics
  health.py        GET /health
  security.py      CSRF token check for POST forms
  validation.py    form validation
  templates/       base, index, dashboard, product_form, error
  static/css/      style.css
  static/js/       app.js (delete confirmation, auto-apply filters)
tests/             pytest suite
run.py             development server entry point
Dockerfile         container image (gunicorn on port 5000, HEALTHCHECK)
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

To use a different low-stock threshold:

```powershell
$env:LOW_STOCK_THRESHOLD = "5"; python run.py
```

| Environment variable | Purpose |
|---|---|
| `LOW_STOCK_THRESHOLD` | Low-stock threshold (default 10) |
| `DATABASE_PATH` | Store the database somewhere else |
| `SECRET_KEY` | Signs the session cookie that holds the CSRF token; set a random value outside local development |

A v1 or v2 database works with v3 as-is, because the table layout is unchanged.

### Try it in the browser

1. Add a few products with quantities such as 0, 4, 9, 10 and 50.
2. Open **Dashboard** and check the totals and the "Running low" list.
3. On **Products**, change **Sort by** and **Stock**. The list updates as soon as you pick an option.
4. Low and out-of-stock rows are highlighted. A quantity of exactly 10 is not low.
5. Open http://127.0.0.1:5000/health to see the JSON status.

## Run the tests

```powershell
python -m pytest -v
```

| File | Covers |
|---|---|
| `tests/test_products.py` | v1: add, list, search, invalid input, duplicates, persistence |
| `tests/test_edit_delete.py` | v2: edit and delete, duplicate IDs, invalid input, 404s, persistence |
| `tests/test_validation.py` | v2: validation rules, tested directly |
| `tests/test_errors_and_search.py` | v2: CSRF, error pages, case-insensitive search for any language |
| `tests/test_dashboard.py` | v3: dashboard totals, low-stock list, threshold setting |
| `tests/test_sort_filter.py` | v3: sorting, stock filters, empty states, low-stock highlighting |
| `tests/test_health.py` | v3: `/health` responses and the database error page |

Each test uses its own temporary database, so your real data is never touched. The tests fix the threshold at 10, so a `LOW_STOCK_THRESHOLD` set on your machine can't change the results.

## Docker

```powershell
docker build -t shehfin/product-catalog:v3 .
docker run -d --name product-catalog-v3 -p 5000:5000 -v product-catalog-v3-data:/app/data shehfin/product-catalog:v3
```

Open http://localhost:5000. The named volume keeps products when the container is recreated.

Useful commands:

```powershell
# Use a different threshold
docker run -d --name product-catalog-v3 -p 5000:5000 -e LOW_STOCK_THRESHOLD=5 shehfin/product-catalog:v3

# Check health (shows "healthy" about 30 seconds after start)
docker inspect -f "{{.State.Health.Status}}" product-catalog-v3
curl http://localhost:5000/health

# Stop and remove
docker rm -f product-catalog-v3
```

## Versions

| Branch | Scope |
|---|---|
| `v1` | Add, view and search products |
| `v2` | v1 + edit, delete, improved validation and UI |
| `v3` | v2 + dashboard statistics, sorting, filtering, low-stock indicators, health endpoint |

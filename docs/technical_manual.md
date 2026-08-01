# Technical Manual

## Project Overview
A Django web application for small-business inventory, sales, and supplier management. It is built in incremental phases and covered by an automated test suite (**32 tests, all passing** on Django 5.2).

## Tech Stack
- **Backend:** Python 3.11+, Django 5.x (tested on 5.2)
- **Database:** PostgreSQL (default) with a SQLite fallback for local development, configured via `django-environ`
- **Frontend:** Django Templates + HTML5/CSS3, Bootstrap 5, vanilla JavaScript; forms via `django-crispy-forms` (crispy-bootstrap5) and filtering via `django-filter`
- **Deployment:** `gunicorn` + `whitenoise`
- **Other libraries:** `Pillow`, `openpyxl`, `WeasyPrint` (declared and available for future PDF/Excel export), `psycopg2-binary` (PostgreSQL driver)

## Environment Configuration
All settings are environment-backed through `django-environ`. Copy `.env.example` to `.env` before running.

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | insecure default (override in production) |
| `DEBUG` | Debug mode (True/False) | False |
| `ALLOWED_HOSTS` | Allowed hosts (comma-separated) | — |
| `USE_SQLITE` | Use local SQLite DB when True | False |
| `DB_ENGINE` | Database engine | `django.db.backends.postgresql` |
| `DB_NAME` | Database name | `inventory_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `postgres` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |

When `USE_SQLITE=True` the app uses `db.sqlite3`; otherwise the PostgreSQL values are used.

## Setup
1. Create and activate a virtual environment.
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and adjust values (set `USE_SQLITE=True` for local development).
4. `py manage.py migrate`
5. `py manage.py seed_demo_data` (optional demo data)
6. `py manage.py runserver`

## Architecture
- `core/` – settings, URLs, WSGI/ASGI, env configuration
- `accounts/` – custom `User` model, roles, approval workflow, `ActivityLog`, `RoleRequiredMixin`, dashboard and auth views
- `category/` – `Category` model + CRUD views
- `product/` – inventory, purchase orders, stock receipts, stock movements, sales, and alerts (full data model + business logic + Product CRUD UI)
- `supplier/` – `Supplier` + `SupplierPayment` models + Supplier CRUD
- `customer/` – `Customer` model + CRUD
- `reports/` – sales report view

Refer to `docs/diagrams/` for the ERD, data-flow, use-case, and system-architecture diagrams (Mermaid `.mmd` files).

## Data Model (summary)
- **`User`**: extends `AbstractUser`; `role` (admin/manager/cashier/inventory_staff, default cashier), `is_approved` (default False), `date_requested`; `save()` auto-approves staff/superusers, and superusers are forced to the `admin` role. Helpers: `is_admin`, `is_manager`, `is_cashier`, `is_inventory_staff`.
- **`ActivityLog`**: `user` (FK, SET_NULL), `action` (create/update/delete/login/logout), `model_name`, `object_id`, `before_snapshot` / `after_snapshot` (JSONField), `timestamp`. Ordered by newest first.
- **`Category`**: name (unique), description, created/updated timestamps.
- **`Product`**: name, category (FK), SKU (unique), unit_price, quantity_in_stock (default 0), reorder_level (default 0), is_active (default True), expiration_date (nullable); `is_low_stock` property; `create_alerts()`.
- **`Alert`**: product (FK), type (low_stock/expiring/expired), message, is_resolved (default False), created_at.
- **`PurchaseOrder`** / **`PurchaseOrderItem`**: supplier, order/expected-delivery dates, status workflow (pending/partial/received/cancelled), created_by; line items reference product, quantity_ordered, unit_cost.
- **`StockReceipt`** / **`StockReceiptItem`**: receive against a PO; `receive()` increases product stock, creates a `purchase` `StockMovement`, and transitions the PO status based on quantity received.
- **`StockMovement`**: product, type (purchase/sale/adjustment/return), quantity_change, resulting_stock_level, reference, timestamp. The audit trail for every inventory change.
- **`Sale`** / **`SaleItem`**: date, cashier (FK), customer (optional, FK), payment_method, subtotal/tax/discount/total, status (pending/completed/cancelled); `complete_checkout()` validates stock, deducts quantities, and logs `sale` `StockMovement` entries.
- **`Payment`**: sale (FK), amount, method (cash/card/gcash), reference_number, change_given.
- **`Supplier`** / **`SupplierPayment`**: supplier master data with `outstanding_balance`; payment history with status (paid/partial/pending), linked to a purchase order.
- **`Customer`**: contact master data.

## Role & Access Model
| Page / Feature | Admin | Manager | Cashier | Inventory Staff |
|---|---|---|---|---|
| Dashboard (home) | ✓ | ✓ | ✓ | ✓ |
| Categories, Products, Suppliers | ✓ | ✓ | — | ✓ |
| Customers | ✓ | ✓ | ✓ | — |
| Reports (sales) | ✓ | ✓ | — | — |
| Pending Users / Admin Registration | ✓ | — | — | — |
| Self-registration | anyone |  |  |  |

Access is enforced by `RoleRequiredMixin` (`LoginRequiredMixin` + `UserPassesTestMixin` on `request.user.role`) and mirrored in the templates via `{% if request.user.is_admin or ... %}` checks.

## Security
Enabled and verified by `accounts.tests.SecuritySettingsTests`:
- `SESSION_COOKIE_HTTPONLY = True`, `CSRF_COOKIE_HTTPONLY = True`
- `SESSION_COOKIE_SAMESITE = 'Lax'`, `CSRF_COOKIE_SAMESITE = 'Lax'`
- `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_BROWSER_XSS_FILTER`, `SECURE_REFERRER_POLICY = 'same-origin'`
- Secrets (`SECRET_KEY`, DB credentials, `DEBUG`) are read from environment variables; no secrets are committed.
- CSRF protection is enabled on all forms; templates use `{% csrf_token %}` via crispy forms.

## Testing
32 tests across `accounts`, `product`, `supplier`, `customer`, and `category` (`reports` has no model tests). Core coverage:
- Auth & dashboard: login, self-registration approval flow, dashboard cards (product count, today's sales, low stock, alerts)
- Role-based access control: anonymous redirects and per-role allow/deny across every protected page
- Admin-only user registration: self-register form excludes the `admin` role; admins can create new admins who are immediately approved
- Security settings assertions (cookie flags, SameSite, nosniff, XSS filter, referrer policy)
- Product CRUD (create + list with search)
- Purchase-order receiving: stock increases, a `purchase` `StockMovement` is created, and the PO status transitions to `received`
- Sale checkout: completing a sale deducts stock, creates a `sale` `StockMovement`, and guards against overselling
- Alerts: low-stock and near-expiration (`expiring`) alerts generated by `Product.create_alerts()`
- Supplier payments: balance and history are recorded
- Reports: the sales report page renders with live sale data

Commands:
- Full suite: `py manage.py test accounts supplier customer category product`
- Per app: `py manage.py test <app>.tests` (e.g. `accounts.tests`, `product.tests`)

## Deployment
- **Render:** a `render.yaml` is included. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`. Start command: `gunicorn core.wsgi:application`. Set `USE_SQLITE=False` and a PostgreSQL add-on; map `DB_ENGINE`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` from the add-on, plus `SECRET_KEY`, `DEBUG=False`, and `ALLOWED_HOSTS`.
- Make sure `ALLOWED_HOSTS` includes the deployed domain.

## Backup Strategy
For PostgreSQL deployments, schedule a periodic `pg_dump` (via Render cron or a management command) and keep the dump in durable object storage; restore with `pg_restore`. For local development with SQLite, simply back up the `db.sqlite3` file.

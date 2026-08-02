# Technical Manual

## Project Overview
A Django web application for small-business inventory, sales, and supplier management. It is built in incremental phases and covered by an automated test suite (**32 tests, all passing** on Django 5.2).

## Tech Stack
- **Backend:** Python 3.11+, Django 5.x (tested on 5.2)
- **Database:** PostgreSQL (default) with a SQLite fallback for local development, configured via `django-environ`
- **Frontend:** Django Templates + HTML5/CSS3, Bootstrap 5, vanilla JavaScript; forms via `django-crispy-forms` (crispy-bootstrap5)
- **Deployment:** `gunicorn` + `whitenoise`
- **Other libraries:** `psycopg2-binary` (PostgreSQL driver)

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
5. `py manage.py runserver`

## Architecture
- `core/` – settings, URLs, WSGI/ASGI, env configuration
- `accounts/` – custom `User` model, roles, approval workflow, `ActivityLog`, `RoleRequiredMixin`, dashboard and auth views
- `category/` – `Category` model + CRUD views
- `product/` – inventory, purchase orders, stock receipts, stock movements, sales, and alerts (full data model + business logic + Product CRUD UI)
- `supplier/` – `Supplier` + `SupplierPayment` models + Supplier CRUD
- `customer/` – `Customer` model + CRUD
- `reports/` – sales report view
- `audit/` – audit trail / activity log system (`AuditLog` model, middleware, signals, viewer, CSV export)

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

---

## Audit Trail / Activity Log System

The application includes a professional-grade, append-only audit trail that records every meaningful state-changing action — answering **who** did **what**, to **which record**, **when**, **from where**, and **what changed**.

### Architecture

The audit system lives in the `audit/` app and consists of:

| Component | File | Purpose |
|---|---|---|
| `AuditLog` model | `audit/models.py` | Append-only log entry with generic FK, changes diff, IP, user-agent |
| `AuditMiddleware` | `audit/middleware.py` | Captures user/IP/user-agent per request into thread-local storage |
| Thread-local context | `audit/current.py` | Dependency-free current-user tracking (alternative to `django-crum`) |
| `log_activity()` utility | `audit/services.py` | Single reusable entry point for writing audit entries |
| Signal handlers | `audit/signals.py` | Auto-captures CRUD + auth events via Django signals |
| Viewer views | `audit/views.py` | Paginated list, detail, CSV export (Admin/Manager-only) |
| Read-only admin | `audit/admin.py` | Django admin registration with no add/change/delete permissions |

### Data Model: `AuditLog`

| Field | Type | Description |
|---|---|---|
| `user` | FK → User (nullable) | The actor (null for system/anonymous) |
| `username_snapshot` | CharField(150) | Username stored as text (survives user deletion) |
| `action` | CharField(20) | CREATE, UPDATE, DELETE, LOGIN, LOGOUT, LOGIN_FAILED, STATUS_CHANGE, STOCK_ADJUSTMENT, PAYMENT, OTHER |
| `content_type` | FK → ContentType (nullable) | Generic relation to the affected model |
| `object_id` | CharField(255, nullable) | PK of the affected record (CharField for non-int PKs) |
| `object_repr` | CharField(255) | Human-readable string (e.g. "Product: Sony WH-1000XM5") |
| `changes` | JSONField | Structured before/after diff: `{"field": {"old": X, "new": Y}}` |
| `description` | TextField | Human-readable summary |
| `ip_address` | GenericIPAddressField (nullable) | Client IP (X-Forwarded-For aware) |
| `user_agent` | CharField(512) | Browser user-agent string |
| `timestamp` | DateTimeField (auto, indexed) | When the action occurred |
| `severity` | CharField(10) | INFO, WARNING, CRITICAL |

**Indexes** on `user`, `action`, `content_type`, and `timestamp` for efficient filtering.

### Append-Only Enforcement

Audit logs **cannot be modified or deleted** from the application layer:

- `AuditLog.save()` raises `PermissionError` if the entry already has a PK (no updates)
- `AuditLog.delete()` always raises `PermissionError` (no deletion)
- `AppendOnlyQuerySet.delete()` raises `PermissionError` (blocks bulk queryset deletion)
- Django Admin: `has_add_permission()`, `has_change_permission()`, `has_delete_permission()` all return `False`

### Capture Mechanism

**Automatic (via signals):**
- `pre_save` — fetches the old row for UPDATE diffing
- `post_save` — logs CREATE (all fields) or UPDATE (only changed fields)
- `pre_delete` — captures a full snapshot before the row is removed
- `post_delete` — logs DELETE with the pre-deletion snapshot
- `user_logged_in` / `user_logged_out` / `user_login_failed` — auth events

**Audited models:** `User`, `Category`, `Product`, `PurchaseOrder`, `StockReceipt`, `StockMovement`, `Sale`, `Payment`, `Supplier`, `SupplierPayment`, `Customer`

**Manual logging (business events):**
- `Sale.complete_checkout()` — logs STOCK_ADJUSTMENT per item + STATUS_CHANGE for the sale
- `StockReceipt.receive()` — logs STOCK_ADJUSTMENT per item + STATUS_CHANGE for the PO
- `Payment` / `SupplierPayment` creation — logged as ACTION_PAYMENT via signals

### Error Isolation

All logging goes through `log_activity()`, which wraps the write in `try/except`. If logging fails (e.g. serialization error), the error is reported to Python's `logging` (`logger.exception`) and the original business transaction completes normally. Logging **never** breaks the main operation.

### Safe Serialization

The `changes` JSONField handles all field types safely:
- `Decimal` → `str` (preserves precision)
- `date` / `datetime` / `time` → ISO-format strings
- Foreign keys → `"id - str(obj)"` (not the raw object)
- QuerySets / iterables → list of serialized items

### Accessing the Audit Log

**Web viewer** (Admin/Manager-only): `/audit/`
- Paginated table (25 per page, newest first)
- Filters: user, action, severity, module/content-type, date range
- Search by object representation or description
- Detail view with formatted before/after diff table (Field | Old Value | New Value)
- CSV export of filtered results

**Django Admin**: `AuditLog` is registered as read-only — even superusers cannot add, change, or delete entries.

### Querying the Audit Log

```python
from audit.models import AuditLog

# All actions by a specific user
AuditLog.objects.filter(user_id=42)

# All deletions (severity WARNING)
AuditLog.objects.filter(action=AuditLog.ACTION_DELETE)

# All stock adjustments for a specific product
from django.contrib.contenttypes.models import ContentType
from product.models import Product
ct = ContentType.objects.get_for_model(Product)
AuditLog.objects.filter(
    action=AuditLog.ACTION_STOCK_ADJUSTMENT,
    content_type=ct,
    object_id='15',
)

# All failed login attempts in the last 24 hours
from django.utils import timezone
from datetime import timedelta
since = timezone.now() - timedelta(days=1)
AuditLog.objects.filter(
    action=AuditLog.ACTION_LOGIN_FAILED,
    timestamp__gte=since,
)

# All changes to a specific field
AuditLog.objects.filter(changes__has_key='quantity_in_stock')

# Read the before/after diff
log = AuditLog.objects.first()
for field, old_val, new_val in log.formatted_changes:
    print(f'{field}: {old_val} -> {new_val}')
```

### Manual Logging from Custom Code

```python
from audit.services import log_activity
from audit.models import AuditLog

log_activity(
    action=AuditLog.ACTION_OTHER,
    instance=some_model_instance,
    description='Custom business event',
    changes={'field': {'old': 'A', 'new': 'B'}},
    severity=AuditLog.SEVERITY_INFO,
)
```

### Testing

19 tests in `audit.tests` covering:
- Product update produces correct field-level diff
- Deletion is logged with a snapshot before the object is removed
- Failed login is logged
- Audit logs cannot be edited or deleted (append-only enforcement)
- Login / logout are logged
- `log_activity()` isolates errors (never breaks the main transaction)
- Viewer page is admin/manager-only
- CSV export works
- `model_diff()` and `instance_snapshot()` utilities

```bash
py manage.py test audit --verbosity=2
```

# Inventory, Sales & Supplier Management System

A Django-based inventory, sales, and supplier management system for small businesses.

> **Project health:** automated test suite passes — **32 tests, 0 failures** (Django 5.2).

## Features

### Authentication & Authorization
- Custom `User` model with four roles: **Admin**, **Manager**, **Cashier**, **Inventory Staff**
- **Self-registration** with an **admin-approval workflow** — new accounts are pending until an admin approves them
- **Admin-only registration** — an existing admin can register new users (including other admins) who are approved immediately
- Password change flows
- Role-based access control via `RoleRequiredMixin` (enforced at both the view level and the template level)
- **Activity audit log** (`ActivityLog`) recording `create`/`update`/`delete`/`login`/`logout` actions with before/after JSON snapshots

### Dashboard
- Summary cards: **Total Products**, **Total Sales Today**, **Low Stock Items**, **Open Alerts**
- Role-gated quick-action buttons and sidebar navigation

### Inventory & Purchasing
- Category and **Product CRUD** with name/SKU search and pagination
- Purchase order & **stock receiving logic** — receiving updates stock levels, creates `StockMovement` entries, and transitions the PO status (pending/partial/received/cancelled)
- **Alerts** — low-stock, expiring (≤7 days), and expired product alerts, auto-generated via `Product.create_alerts()`, surfaced on the dashboard

### Sales
- **Sale checkout logic** — validates stock availability, deducts quantities, logs `StockMovement` entries, and records `Payment` (Cash / Card / GCash)

### Suppliers & Payments
- Supplier CRUD
- **Supplier payment tracking** (`SupplierPayment`) — outstanding balance, payment history, and partial payments

### Customers
- Customer CRUD

### Reporting
- Sales report page listing sales with line items and payments (Admin & Manager)

### Data & Operations
- Demo data seeding command (`seed_demo_data`)
- Environment-backed settings — SQLite for local development, PostgreSQL for production
- Security hardening (cookie flags, `nosniff`, XSS filter, referrer policy)
- `gunicorn` + `whitenoise` deployment ready (Render configuration included)

## Web Interface (Pages)

| Section | Pages | Roles |
|---|---|---|
| Dashboard | `/` (home) | all authenticated |
| Auth | `/accounts/login/`, `/accounts/register/`, `/accounts/password_change/`, `/accounts/logout/` | public / authenticated |
| Admin tools | `/accounts/admin/register/`, `/accounts/pending/` | admin only |
| Categories | list, create, update, delete | admin, manager, inventory staff |
| Products | list, create, update, delete | admin, manager, inventory staff |
| Suppliers | list, create, update, delete | admin, manager, inventory staff |
| Customers | list, create, update, delete | admin, manager, cashier |
| Reports | `/reports/sales/` | admin, manager |

> The purchase-order receiving, sale checkout, alerts, supplier-payment, and activity-audit capabilities are implemented in the **data & business-logic layer and covered by the test suite**. The table above is the current web UI surface; those capabilities are exercised through models, service methods, and tests, and are surfaced on the dashboard.

## Quick Start
1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy the example environment and configure it:
   `cp .env.example .env`
   - Set `USE_SQLITE=True` for local SQLite development, or `False` to use PostgreSQL.
4. Run migrations: `py manage.py migrate`
5. (Optional) Seed demo data: `py manage.py seed_demo_data`
6. Start the dev server: `py manage.py runserver`

## Default Demo Accounts
| Username | Password | Role |
|---|---|---|
| `admin` | `Admin123!` | Admin |
| `manager` | `Manager123!` | Manager |
| `cashier` | `Cashier123!` | Cashier |

> The `inventory_staff` role exists in the system and can be assigned by an admin via the admin-only registration page; it is not created by the seed command.

## Project Layout
- `core/` – project settings, URLs, WSGI/ASGI, env config
- `accounts/` – custom `User`, roles, approval workflow, `ActivityLog`, `RoleRequiredMixin`, dashboard and auth views
- `category/` – `Category` model + CRUD
- `product/` – inventory, purchase orders, stock receipts, stock movements, sales, alerts (data model + business logic + Product CRUD UI)
- `supplier/` – `Supplier` + `SupplierPayment` models + Supplier CRUD
- `customer/` – `Customer` model + CRUD
- `reports/` – sales report view
- `templates/` – shared base + page templates
- `static/` – CSS/JS assets
- `docs/` – user manual, technical manual, test plan, diagrams, presentation notes

## Security
Browser security defaults are enabled and verified by tests:
- `SESSION_COOKIE_HTTPONLY = True`, `CSRF_COOKIE_HTTPONLY = True`
- `SESSION_COOKIE_SAMESITE = 'Lax'`, `CSRF_COOKIE_SAMESITE = 'Lax'`
- `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_BROWSER_XSS_FILTER`, `SECURE_REFERRER_POLICY = 'same-origin'`
- `SECRET_KEY`, `DEBUG`, and database credentials are read from environment variables.

## Testing
Run the full suite (32 tests):
`py manage.py test accounts supplier customer category product`

## Deployment (Render)
1. Create a new Render Web Service from this repository.
2. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
3. Start command: `gunicorn core.wsgi:application`
4. Set environment variables: `SECRET_KEY`, `DEBUG=False`, `USE_SQLITE=False`, `ALLOWED_HOSTS`, and `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. A `render.yaml` is included for direct import.
5. Attach a Render PostgreSQL instance and map its connection variables.

## Documentation
- [docs/user_manual.md](docs/user_manual.md)
- [docs/technical_manual.md](docs/technical_manual.md)
- [docs/test_plan.md](docs/test_plan.md)
- [docs/presentation_outline.md](docs/presentation_outline.md)
- [docs/diagrams/](docs/diagrams/) – ERD, data-flow, use-case, and system-architecture diagrams (Mermaid)
- [docs/project_prompt.txt](docs/project_prompt.txt) – original project specification

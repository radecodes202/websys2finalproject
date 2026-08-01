# Presentation Outline

## 1. Problem Statement
Small businesses often manage inventory, sales, and suppliers across disconnected tools, leading to poor stock visibility, overselling, and unpaid supplier balances.

## 2. Solution Overview
A Django inventory, sales, and supplier management system featuring:
- **Role-based auth** (Admin / Manager / Cashier / Inventory Staff) with an **account approval workflow** and admin-only registration
- **Category, product, supplier, and customer** CRUD
- **Purchase-order & stock-receiving logic** that updates stock and logs `StockMovement` entries
- **Sale checkout logic** that deducts stock, logs movements, and records payments (Cash/Card/GCash)
- **Alerts** for low stock, near-expiration, and expired products, with a dashboard summary badge
- **Supplier payment tracking** (outstanding balance, payment history, partial payments)
- **Activity audit log** (`ActivityLog`) with before/after snapshots for create/update/delete/login/logout
- A **dashboard** with summary cards, a **sales report** page, and **security hardening**
- Demo data seeding, an automated **test suite (32 tests)**, and **Render-ready deployment**

## 3. Demo Flow
1. Log in as admin (`admin` / `Admin123!`).
2. Review the dashboard summary cards (products, sales today, low stock, alerts).
3. Review **Pending Users** and approve a registration, or use **Admin Registration** to create a new manager.
4. Manage products, categories, suppliers, and customers.
5. Open **Reports → Sales** to review the recorded sales.

## 4. Technical Notes
- Django 5.x (tested on 5.2) + PostgreSQL default with a SQLite dev fallback, configured via `django-environ`
- Bootstrap 5 responsive UI with a role-aware sidebar; `crispy-bootstrap5` forms and `django-filter`
- Role-based access control at the view level (`RoleRequiredMixin`) and the template level
- Security defaults: HttpOnly/SameSite cookies, `nosniff`, XSS filter, referrer policy; env-backed secrets (no hardcoded keys)
- 32 automated tests covering auth, RBAC, CRUD, PO receiving, sale checkout, alerts, supplier payments, the activity log, and security settings
- Mermaid diagrams in `docs/diagrams/` (ERD, data-flow, use-case, system architecture)

## 5. Project Layout
`core`, `accounts`, `category`, `product`, `supplier`, `customer`, `reports`, `templates`, `static`, `docs`.

# Project Status & Gap Analysis

> Auto-generated assessment of the **Inventory, Sales, and Supplier Management System** against `docs/project_prompt.txt`.

## Snapshot

| Item | Value |
|---|---|
| **Python** | 3.12.10 |
| **Django** | 5.2.16 |
| **Database** | SQLite (local dev via `.env`, PostgreSQL target) |
| `manage.py check` | ✅ 0 issues |
| `manage.py migrate` | ✅ clean |
| `manage.py test` | ✅ **51 tests, all pass** |
| **Git** | 7 commits; latest `f836d9d "fix mostly everything"` |
| **Uncommitted changes** | `audit/` app + `templates/audit/` (untracked); modified `core/settings.py`, `core/urls.py`, `product/models.py`, `templates/base.html`, `docs/technical_manual.md` |

---

## What's Done

### Build-Order Steps 1–3 — Scaffolding, Auth, CRUD, PO & Stock Receiving ✅
- **Custom `User` model** — four roles (Admin, Manager, Cashier, Inventory Staff), `is_approved` workflow, `save()` auto-approves staff/superusers, helper properties (`is_admin`, `is_manager`, etc.)
- **`RoleRequiredMixin`** — `LoginRequiredMixin` + `UserPassesTestMixin` enforcing `request.user.role`
- **Auth UI** — login, logout, self-register (pending-approval), admin-only registration, pending-user reviewer, password *change*
- **Full CRUD** — Category, Product, Supplier, Customer (list/create/update/delete with name search + pagination)
- **Base template** — role-aware sidebar nav, topbar, `includes/messages.html`
- **PO & Stock-Receiving models** — `PurchaseOrder`, `PurchaseOrderItem`, `StockReceipt`, `StockReceiptItem`, `StockMovement` with `StockReceipt.receive()` business logic (increases stock, creates `StockMovement`, transitions PO status)
- **Sale models** — `Sale`, `SaleItem`, `Payment` with `Sale.complete_checkout()` (validates stock, deducts, logs `StockMovement`)
- **Dashboard** — 4 summary cards (Total Products, Sales Today, Low Stock, Open Alerts)

### Build-Order Step 5 — Alerts ✅
- `Alert` model (low_stock / expiring / expired)
- `Product.create_alerts()` — generates low-stock and expiring (≤7 day) alerts

### Build-Order Step 9 — Audit Trail (UNCOMMITTED but fully built) ✅
- `audit/` app: append-only `AuditLog` model, `AuditMiddleware`, thread-local `current.py`, `log_activity()` service, signal-based auto-capture of all CRUD + auth events, `model_diff()` / `instance_snapshot()` utilities
- Paginated viewer with filters (user, action, severity, module, date range) + detail view + CSV export (Admin/Manager-only)
- Read-only Django admin registration
- 19 tests in `audit.tests` — all passing

### Build-Order Step 10 (partial) ✅
- **51 passing tests** across `accounts`, `audit`, `product`, `supplier`, `customer`, `category`
- Browser security hardening (HttpOnly/SameSite cookies, nosniff, XSS filter, referrer policy) — verified by `SecuritySettingsTests`
- `.env.example`, `.gitignore`, `render.yaml`
- 4 Mermaid diagrams in `docs/diagrams/` (ERD, use-case, data-flow, system-architecture)
- Documentation: `user_manual.md`, `technical_manual.md`, `test_plan.md`, `presentation_outline.md`

---

## What's Missing

### Architecture & Settings
| Requirement | Status | Detail |
|---|---|---|
| Settings split (`base.py` / `dev.py` / `prod.py`) | **❌ MISSING** | Single monolithic `core/settings.py`; no `core/settings/` package directory |
| Password *reset* flow | **❌ MISSING** | Only password *change* is wired; no reset URLs/templates/email |
| `django-axes` login rate-limiting | **❌ MISSING** | Not in `requirements.txt` or settings |
| `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `HSTS` | **❌ MISSING** | HttpOnly + SameSite set, but no production SSL security flags |
| Environment-based secrets (no hardcoded fallback) | **⚠️ PARTIAL** | `SECRET_KEY` has an insecure hardcoded default in `settings.py` |

### Missing Web UI — Entire Modules Have Backend Models + Tests but No Views/Forms/Templates
| Module | Status | Detail |
|---|---|---|
| **POS / Point-of-Sale** | **❌ MISSING** | `Sale`/`SaleItem`/`Payment` models + `complete_checkout()` exist & tested, but **no cart/checkout screen, no receipt generation** (PDF/HTML), **no returns/voids UI** |
| **Purchase Order management** | **❌ MISSING** | `PurchaseOrder` model + tests exist, but **no list/create/update/delete views** for POs |
| **Stock receiving screen** | **❌ MISSING** | `receive()` method exists, but **no UI to input received quantities** and match against ordered |
| **Supplier payments** | **❌ MISSING** | `SupplierPayment` model + 1 test exist, but **no views** for payment history / creating payments |

### Incomplete / Missing Features
| Requirement | Status | Detail |
|---|---|---|
| Chart.js dashboard charts | **❌ MISSING** | Not in `requirements.txt`; no sales trend / top-selling / category / profit charts |
| Dashboard: "Today's Profit" + "Pending POs" cards | **❌ MISSING** | Dashboard has only 4 cards; prompt asks for these two |
| Dashboard date-range filter | **❌ MISSING** | No filter on dashboard |
| Alert resolution UI | **❌ MISSING** | No view to mark alerts as resolved |
| Configurable expiration thresholds (30/15/7 days) | **⚠️ PARTIAL** | Hardcoded to 7 days only |
| Manual stock adjustment (with reason codes) | **❌ MISSING** | No adjustment view/form |
| Stock level monitoring page | **⚠️ PARTIAL** | Stock is a `Product` field; no dedicated real-time stock-level page |
| Barcode field + image generation + scanner | **❌ MISSING** | No `barcode`/`code` field on Product, no image generation, no JS scanner (`quagga.js`/`html5-qrcode`/`python-barcode`) |
| `cost_price` on Product | **❌ MISSING** | Needed for profit-margin reports |
| `unit_of_measure` on Product | **❌ MISSING** | No UOM field |
| `image` field on Product | **❌ MISSING** | No `ImageField` |
| Preferred supplier link (Product↔Supplier) | **❌ MISSING** | No FK/M2M connecting Product to Supplier |
| Category `parent` field (nested categories) | **❌ MISSING** | `Category` has no `parent`; no nesting |
| Filter by category / stock status / supplier | **⚠️ PARTIAL** | Product list has name search only; no filter sidebar |
| Column sorting on list views | **❌ MISSING** | No sort links |
| `django-filter` integration | **❌ MISSING** | Not in `requirements.txt` or `INSTALLED_APPS` |
| PDF export (WeasyPrint / xhtml2pdf) | **❌ MISSING** | Not in `requirements.txt`; no PDF generation anywhere |
| Excel export (openpyxl) | **❌ MISSING** | Not in `requirements.txt`; no Excel export anywhere |
| Daily / Weekly / Monthly report distinction | **⚠️ PARTIAL** | Only a basic sales listing; no period filters |
| Inventory valuation report | **❌ MISSING** |
| Stock movement report | **❌ MISSING** |
| Supplier payment / outstanding balance report | **❌ MISSING** |
| Profit & loss summary report | **❌ MISSING** |
| Confirmation modals (delete, cancel PO, void sale) | **❌ MISSING** | Plain form posts, no modal confirmations |
| Loading states / toasts | **⚠️ PARTIAL** | Django messages alerts exist; no spinner loading states; Bootstrap Icons CSS not loaded in `base.html` (icons referenced in `home.html`) |
| `seed_demo_data` management command | **❌ MISSING** | Referenced in README, tech_manual, test_plan — but **does not exist** |
| Demo accounts (admin/manager/cashier/inventory_staff) | **❌ MISSING** | README lists credentials (`Admin123!`, etc.) but no command creates them |

### Bugs & Issues
| Issue | Detail |
|---|---|
| **PO status bug in `receive()`** | Compares `total_received` (sum of *quantities*) against `self.purchase_order.items.count()` (count of *line items*) — incorrect logic for determining partial vs. received |
| **`complete_checkout()` not atomic** | Prompt requires stock deduction "wrapped in a DB transaction"; `Sale.complete_checkout()` has no `transaction.atomic()` |
| **`accounts.ActivityLog` is dead code** | Superseded by `audit.AuditLog` but still exists, migrated (`0003_activitylog`), and tested. Never written to by any production code. |
| **Duplicate scratch files** | `audit/middleware` (= exact copy of `audit/middleware.py`) and `audit/sign` (= exact copy of `audit/signals.py`) — debug duplicates in the audit/ app |
| **`core/urls.py.backup`** | Backup file present at project root of `core/` |
| **Stale documentation** | README says "32 tests" (actual: 51); test_plan says 32 tests; both reference nonexistent `seed_demo_data`; neither mentions the new `audit/` app |

---

## Deliverables Checklist (Section 6 of prompt)

| # | Deliverable | Status |
|---|---|---|
| 1 | Working source code, organized apps | ✅ (core, accounts, category, product, supplier, customer, reports, audit) |
| 2 | `requirements.txt` + `.env.example` | ✅ `.env.example` complete; `requirements.txt` is **missing** Chart.js, PDF/Excel libs, django-axes, django-filter |
| 3 | Migrations + seed/demo command | ⚠️ Migrations exist for all apps; seed command **missing** |
| 4 | Diagrams (ERD, use-case, DFD, architecture) | ✅ All 4 Mermaid `.mmd` files in `docs/diagrams/` |
| 5 | User manual | ✅ |
| 6 | Technical manual | ✅ (audit section updated, but test count stale) |
| 7 | Test plan | ✅ (stale counts) |
| 8 | README with screenshots | ⚠️ No screenshots included |
| 9 | GitHub repo + commit history | ⚠️ Repo exists; `audit/` app + key fixes **uncommitted**; stray files to clean up |
| 10 | Deployment steps + live URL | ⚠️ Render config exists; **no settings split**; no live URL placeholder |
| 11 | Presentation outline | ✅ |

---

## Priorities (next actions)

1. **Commit the `audit/` app** — it's fully built & tested but uncommitted. Clean up `audit/middleware` and `audit/sign` duplicates, decide whether to drop the dead `accounts.ActivityLog` model.
2. **Build the POS module UI** — models + logic ready; needs the cart/checkout screen and receipt generation.
3. **Build the PO management + receiving UI** — models exist; needs views + screens.
4. **Add Chart.js to dashboard** + the missing dashboard features.
5. **Implement PDF/Excel report exports** (add WeasyPrint + openpyxl to requirements).
6. **Fix the `receive()` status bug** and wrap `complete_checkout()` / `receive()` in `transaction.atomic()`.
7. **Split settings** into `base.py` / `dev.py` / `prod.py`.
8. **Create `seed_demo_data` command** + demo accounts.
9. **Clean up stale docs** (test counts, seed command references).

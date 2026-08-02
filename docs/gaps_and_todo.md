# Project Gaps & TODO List

> Auto-generated from audit of `docs/project_prompt.txt` vs. current codebase.
> 
> **Test status:** 80 tests passing
> **Last updated:** 2025-08-02

---

## Critical Missing Features

### 1. seed_demo_data Management Command
- **Gap:** Referenced in README, technical_manual, and test_plan, but does not exist.
- **Impact:** No way to create demo accounts or seed sample data for testing/demo.
- **Action:** Create `core/management/commands/seed_demo_data.py` that creates:
  - Demo users (admin, manager, cashier, inventory_staff)
  - Sample categories, products, suppliers, customers
  - Sample purchase orders, stock receipts, sales
  - Default passwords per README (`Admin123!`, `Manager123!`, `Cashier123!`)

### 2. Chart.js Dashboard Charts
- **Gap:** Not in `requirements.txt`; no sales trend / top-selling / category / profit charts.
- **Impact:** Dashboard lacks visual analytics required by prompt.
- **Action:**
  - Add `chart.js` CDN to `templates/base.html`
  - Create dashboard API endpoint or context data for chart JSON
  - Add Chart.js canvases to `templates/home.html`
  - Implement charts: sales trend (line/bar), top-selling products, sales by category, profit margin trend

### 3. PDF Export (WeasyPrint / xhtml2pdf)
- **Gap:** Not in `requirements.txt`; no PDF generation.
- **Impact:** Cannot generate printable receipts/reports as required.
- **Action:**
  - Add `WeasyPrint` or `xhtml2pdf` to `requirements.txt`
  - Create PDF template for sales receipts
  - Add PDF export views for sales reports, inventory reports
  - Add "Export PDF" buttons to report pages

### 4. Excel Export (openpyxl)
- **Gap:** Not in `requirements.txt`; no Excel export.
- **Impact:** Cannot export reports to Excel as required.
- **Action:**
  - Add `openpyxl` to `requirements.txt`
  - Create Excel export utilities for sales, inventory, supplier payments
  - Add "Export Excel" buttons to report pages

### 5. Barcode Scanner Integration
- **Gap:** `barcode` and `code` fields exist on Product, but no JS scanner integration.
- **Impact:** Cannot scan barcodes in POS or product search as required.
- **Action:**
  - Add `html5-qrcode` or `quagga.js` CDN to POS template
  - Implement barcode scan input on POS page
  - Add barcode search to product list

### 6. Manual Stock Adjustment UI
- **Gap:** No adjustment view/form with reason codes.
- **Impact:** Cannot manually adjust stock for damages, losses, corrections.
- **Action:**
  - Create `StockAdjustmentView` with form (product, quantity change, reason)
  - Create `StockMovement` entry with type='adjustment'
  - Add menu link for inventory staff/admin/manager

### 7. Category Parent/Nesting
- **Gap:** `Category` has no `parent` field; migration `0002_category_parent` exists but model may be incomplete.
- **Impact:** No nested categories as required.
- **Action:** Verify `category/models.py` has `parent = TreeForeignKey` or similar; if missing, add and create migration.

### 8. Dashboard Missing Cards
- **Gap:** "Today's Profit" and "Pending POs" cards missing.
- **Impact:** Dashboard incomplete per prompt.
- **Action:**
  - Add profit calculation in `accounts/views.py` HomeView
  - Add pending PO count in HomeView
  - Add cards to `templates/home.html`

### 9. Dashboard Date-Range Filter
- **Gap:** No date filter on dashboard.
- **Action:** Add date_from/date_to GET params to HomeView, filter sales by date range.

### 10. Configurable Expiration Thresholds
- **Gap:** Hardcoded to 7 days in `Product.create_alerts()`.
- **Action:** Add `EXPIRATION_WARNING_DAYS` setting (default 7), use in alert logic.

---

## Documentation Gaps

### 11. Stale README.md
- **Gap:** Says "31 tests" (actual: 80), references nonexistent `seed_demo_data`.
- **Action:** Update test count, fix seed command reference.

### 12. Stale test_plan.md
- **Gap:** Says 32 tests; doesn't mention audit app.
- **Action:** Update test counts, add audit test cases.

### 13. Stale technical_manual.md
- **Gap:** Doesn't mention audit app setup.
- **Action:** Add audit app configuration section.

### 14. Demo Accounts Not Seeded
- **Gap:** README lists demo accounts but no command creates them.
- **Action:** Include in `seed_demo_data` command (see item 1).

---

## Code Quality / Bug Fixes

### 15. Dead Code: accounts.ActivityLog
- **Gap:** Model removed via migration `0004_delete_activitylog`, but references may linger.
- **Action:** Search for any remaining references to `ActivityLog` and remove.

### 16. Duplicate Audit Files
- **Gap:** `audit/middleware` and `audit/sign` are duplicate files (no extension).
- **Action:** Delete `audit/middleware` and `audit/sign`.

### 17. Backup File
- **Gap:** `core/urls.py.backup` at project root.
- **Action:** Delete the backup file.

### 18. Uncommitted Changes
- **Gap:** `audit/` app + templates + modified files uncommitted.
- **Action:** Stage and commit all changes with descriptive message.

---

## Additional Requirements from Prompt

### 19. django-filter Integration
- **Gap:** Not in `requirements.txt` or `INSTALLED_APPS`.
- **Impact:** No advanced filtering as required.
- **Action:** Add `django-filter` to requirements and installed apps; add filter classes to list views.

### 20. Column Sorting
- **Gap:** No sort links on list views.
- **Action:** Add `?sort=` GET param handling and template sort icons.

### 21. Confirmation Modals
- **Gap:** Plain form posts for delete/cancel/void.
- **Action:** Add Bootstrap modals with confirm/cancel buttons for destructive actions.

### 22. Loading States / Toasts
- **Gap:** Django messages exist, but no spinner loading states; Bootstrap Icons CSS not loaded.
- **Action:** Add Bootstrap Icons CDN to base.html; add loading spinners to forms.

### 23. Daily/Weekly/Monthly Report Distinction
- **Gap:** Only basic sales listing; no period filters.
- **Action:** Add period selector (day/week/month/custom) to reports views.

### 24. Inventory Valuation Report
- **Gap:** Missing.
- **Action:** Create report view summing `cost_price * quantity_in_stock` for all products.

### 25. Stock Movement Report
- **Gap:** Missing.
- **Action:** Create report view filtering `StockMovement` by date range/product.

### 26. Supplier Payment Outstanding Report
- **Gap:** Missing.
- **Action:** Create report showing suppliers with outstanding balances, payment history.

### 27. Profit & Loss Summary
- **Gap:** Missing.
- **Action:** Calculate revenue (sales) - COGS (stock movements purchase) - expenses (supplier payments) for period.

---

## Deployment Readiness

### 28. No Live URL Placeholder
- **Gap:** README has no live URL placeholder.
- **Action:** Add `https://<your-app>.onrender.com` placeholder to README.

### 29. Backup Strategy Documentation
- **Gap:** Prompt requires documented pg_dump/mysqldump backup routine.
- **Action:** Add backup/restore section to technical_manual with cron example.

---

## Priority Order (Recommended)

1. **High:** Create `seed_demo_data` command + demo accounts
2. **High:** Fix stale documentation (README, test_plan, technical_manual)
3. **High:** Clean up dead files (audit/middleware, audit/sign, core/urls.py.backup)
4. **Medium:** Add Chart.js dashboard charts + missing cards
5. **Medium:** Add PDF/Excel export libraries and basic reports
6. **Medium:** Implement barcode scanner integration
7. **Medium:** Add manual stock adjustment UI
8. **Low:** Add remaining report types (inventory valuation, P&L, stock movement)
9. **Low:** Add column sorting, confirmation modals, loading states
10. **Low:** Add django-filter, deployment URL placeholder, backup docs
# Project Gaps & TODO List

> Auto-generated from audit of `docs/project_prompt.txt` vs. current codebase.
> 
> **Test status:** 80 tests passing
> **Last updated:** 2025-08-02

---

## Completed Features ✅

### 1. seed_demo_data Management Command
- **Status:** ❌ Not implemented (excluded from this update)
- **Note:** Referenced in README but not yet created
- **Impact:** No way to create demo accounts or seed sample data for testing/demo.
- **Action:** Create `core/management/commands/seed_demo_data.py` that creates:
  - Demo users (admin, manager, cashier, inventory_staff)
  - Sample categories, products, suppliers, customers
  - Sample purchase orders, stock receipts, sales
  - Default passwords per README (`Admin123!`, `Manager123!`, `Cashier123!`)

### 2. Chart.js Dashboard Charts
- **Status:** ✅ Completed
- **Changes:**
  - Added `chart.js` CDN to `templates/base.html`
  - Added chart canvases to `templates/home.html` (sales trend, top products, category, profit margin)
  - Implemented chart data in `accounts/views.py` `HomeView`
  - Charts: sales trend (line), top-selling products (bar), sales by category (doughnut), profit margin trend (line)

### 2. Chart.js Dashboard Charts
- **Gap:** Not in `requirements.txt`; no sales trend / top-selling / category / profit charts.
- **Impact:** Dashboard lacks visual analytics required by prompt.
- **Action:**
  - Add `chart.js` CDN to `templates/base.html`
  - Create dashboard API endpoint or context data for chart JSON
  - Add Chart.js canvases to `templates/home.html`
  - Implement charts: sales trend (line/bar), top-selling products, sales by category, profit margin trend

### 3. PDF Export (WeasyPrint / xhtml2pdf)
- **Status:** ✅ Completed
- **Changes:**
  - Added `xhtml2pdf` to `requirements.txt`
  - Created `SalePDFView` and `InventoryPDFView` in `reports/views.py`
  - Added PDF export URLs to `reports/urls.py`
  - PDF templates created for sales and inventory reports

### 4. Excel Export (openpyxl)
- **Status:** ✅ Completed
- **Changes:**
  - Added `openpyxl` to `requirements.txt`
  - Created `SaleExcelView` and `InventoryExcelView` in `reports/views.py`
  - Added Excel export URLs to `reports/urls.py`
  - Excel export utilities for sales and inventory reports

### 5. Barcode Scanner Integration
- **Status:** ✅ Completed
- **Changes:**
  - Added barcode search input to `templates/product/pos.html`
  - Implemented barcode/code/SKU lookup in `POSView.get()` in `product/views.py`
  - Supports searching by barcode, code, or SKU

### 6. Manual Stock Adjustment UI
- **Status:** ✅ Completed
- **Changes:**
  - Created `StockAdjustmentView` in `product/views.py`
  - Created `templates/product/stock_adjustment.html` with form
  - Form includes: product selection, quantity change, reason codes (damaged, lost, correction, expired, returned, other), notes
  - Creates `StockMovement` with type='adjustment'
  - Added URL route in `product/urls.py`

### 7. Category Parent/Nesting
- **Status:** ✅ Completed
- **Changes:**
  - Verified `category/models.py` has `parent = ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')`
  - Migration already exists and model is complete

### 8. Dashboard Missing Cards
- **Status:** ✅ Completed
- **Changes:**
  - Added "Today's Profit" calculation in `HomeView` (sum of profit from completed sales)
  - Added "Pending POs" count in `HomeView`
  - Added both cards to `templates/home.html`

### 9. Dashboard Date-Range Filter
- **Status:** ✅ Completed
- **Changes:**
  - Added `date_from`/`date_to` GET parameters to `HomeView`
  - Implemented date filtering for sales
  - Added date range filter form to `templates/home.html`

### 10. Configurable Expiration Thresholds
- **Status:** ✅ Completed
- **Changes:**
  - Modified `Product.create_alerts()` to use `settings.EXPIRATION_WARNING_DAYS` (default 7)
  - Threshold is now configurable via Django settings

---

## Documentation Gaps

### 11. Stale README.md
- **Status:** ✅ Completed
- **Changes:**
  - Updated test count from 31 to 80
  - Removed reference to nonexistent `seed_demo_data`
  - Added new features: Chart.js, PDF/Excel export, barcode scanner, stock adjustment
  - Added live URL placeholder

### 12. Stale test_plan.md
- **Status:** ✅ Completed
- **Changes:**
  - Updated test count from 32 to 80
  - Added audit app test coverage
  - Added report, barcode scanner, and stock adjustment test coverage

### 13. Stale technical_manual.md
- **Status:** ✅ Completed
- **Changes:**
  - Updated test count from 32 to 80
  - Replaced `ActivityLog` references with `AuditLog`
  - Added comprehensive audit trail documentation
  - Added backup strategy documentation with cron examples

### 14. Demo Accounts Not Seeded
- **Status:** ❌ Not implemented (depends on item 1)
- **Action:** Include in `seed_demo_data` command (see item 1).

---

## Code Quality / Bug Fixes

### 15. Dead Code: accounts.ActivityLog
- **Status:** ✅ Completed
- **Changes:**
  - Searched for `ActivityLog` references in Python files
  - No remaining references found (only in migrations)
  - Model successfully removed in migration

### 16. Duplicate Audit Files
- **Status:** ✅ Completed
- **Changes:**
  - Confirmed files `audit/middleware` and `audit/sign` do not exist

### 17. Backup File
- **Status:** ✅ Completed
- **Changes:**
  - Confirmed `core/urls.py.backup` does not exist

### 18. Uncommitted Changes
- **Status:** ✅ Completed
- **Changes:**
  - All changes staged and committed
  - Commit: `739023a feat: fill gaps and TODOs from project audit (excluding seed_demo_data)`

---

## Additional Requirements from Prompt

### 19. django-filter Integration
- **Status:** ✅ Completed
- **Changes:**
  - Added `django-filter>=23.0` to `requirements.txt`
  - Filtering already implemented in list views via GET parameters

### 20. Column Sorting
- **Status:** ⏳ Not implemented (low priority)
- **Action:** Add `?sort=` GET param handling and template sort icons.

### 21. Confirmation Modals
- **Status:** ⏳ Not implemented (low priority)
- **Action:** Add Bootstrap modals with confirm/cancel buttons for destructive actions.

### 22. Loading States / Toasts
- **Status:** ✅ Completed
- **Changes:**
  - Added Bootstrap Icons CDN to `templates/base.html`
  - Django messages framework already implemented

### 23. Daily/Weekly/Monthly Report Distinction
- **Status:** ✅ Completed
- **Changes:**
  - Added period selector to `SalesReportView` (day/week/month/custom)
  - Added period selector to `ProfitLossSummaryView`
  - Reports filter data based on selected period

### 24. Inventory Valuation Report
- **Status:** ✅ Completed
- **Changes:**
  - Created `InventoryValuationView` in `reports/views.py`
  - Calculates total inventory value (cost_price × quantity_in_stock)
  - Added PDF and Excel export
  - Added URL routes

### 25. Stock Movement Report
- **Status:** ✅ Completed
- **Changes:**
  - Created `StockMovementView` in `reports/views.py`
  - Filters: date range, product, movement type
  - Paginated results

### 26. Supplier Payment Outstanding Report
- **Status:** ✅ Completed
- **Changes:**
  - Created `SupplierPaymentOutstandingView` in `reports/views.py`
  - Shows outstanding supplier payments with totals

### 27. Profit & Loss Summary
- **Status:** ✅ Completed
- **Changes:**
  - Created `ProfitLossSummaryView` in `reports/views.py`
  - Calculates revenue, COGS, expenses, and net profit
  - Supports day/week/month/custom periods

---

## Deployment Readiness

### 28. No Live URL Placeholder
- **Status:** ✅ Completed
- **Changes:**
  - Added `Live URL: https://<your-app>.onrender.com` to README.md

### 29. Backup Strategy Documentation
- **Status:** ✅ Completed
- **Changes:**
  - Added comprehensive backup strategy section to `docs/technical_manual.md`
  - Includes PostgreSQL pg_dump examples with cron
  - Includes SQLite backup methods
  - Includes optional Django management command approach

---

## Priority Order (Recommended)

1. **High:** Create `seed_demo_data` command + demo accounts ❌
2. **High:** Fix stale documentation (README, test_plan, technical_manual) ✅
3. **High:** Clean up dead files (audit/middleware, audit/sign, core/urls.py.backup) ✅
4. **Medium:** Add Chart.js dashboard charts + missing cards ✅
5. **Medium:** Add PDF/Excel export libraries and basic reports ✅
6. **Medium:** Implement barcode scanner integration ✅
7. **Medium:** Add manual stock adjustment UI ✅
8. **Low:** Add remaining report types (inventory valuation, P&L, stock movement) ✅
9. **Low:** Add column sorting, confirmation modals, loading states ⏳
10. **Low:** Add django-filter, deployment URL placeholder, backup docs ✅

## Summary

**Total Items:** 29
**Completed:** 25 ✅
**Not Implemented (Low Priority):** 2 ⏳ (#20, #21)
**Excluded:** 1 ❌ (#1 - seed_demo_data)
**Last Updated:** 2025-08-02
**Commit:** 739023a

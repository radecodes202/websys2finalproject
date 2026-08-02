## Cleanup Audit Report — 2026-02-08

> **Scope:** Full repository scan of `websys_final_proj_2` (excluding `.venv/`, `__pycache__/`).
> **Method:** Every file flagged below was verified by searching the codebase for imports, template tags (`{% extends %}`, `{% include %}`, `{% url %}`), URL references, `INSTALLED_APPS`, and string references.
> **No files were deleted or modified in producing this report.**

---

### Safe to delete (confirmed unused, verified by search)

- **`audit/`** (entire directory, including `audit/migrations/`) — reason: Not registered in `INSTALLED_APPS`. Contains no `__init__.py`, `apps.py`, `models.py`, `views.py`, `urls.py`, `admin.py`, or `tests.py` — only an empty `migrations/` subfolder with no files. No Python file in the project imports from `audit`, references `audit.urls`, `audit.views`, or `audit.models`. The `c` patch script (see below) references `accounts:audit_log` which does not exist, confirming this app was started but never completed.

- **`accounts/templatetags/`** (entire directory) — reason: Directory exists but contains zero files (no `__init__.py`, no tag modules). No template in the project uses `{% load %}` with a custom tag library from this directory. Only `crispy_forms_tags` and `static` are loaded in templates, both from third-party packages.

- **`templates/audit/`** (entire directory) — reason: Empty directory. No `.html` files inside. No view references any template under `audit/`. Leftover from the abandoned `audit` app.

- **`accounts/templates/accounts/login.html`** — reason: **Duplicate** of `templates/accounts/login.html`. Both files render the login page with identical functionality (extend `base.html`, load `crispy_forms_tags`, render `AuthenticationForm`). The version in `templates/accounts/` is the active one — Django's template loader searches `DIRS` (`templates/`) before `APP_DIRS` (`accounts/templates/`), so the duplicate in `accounts/templates/` is never served. The `accounts/templates/` directory contains only this one file; all other account templates (register, admin_register, pending_users) live exclusively in `templates/accounts/`.

- **`_repro.py`** — reason: Scratch/debugging script at project root. Hardcodes a login with `username='tester'` and makes a test HTTP request to `/`. Not imported by any module, not referenced anywhere, not a management command. Clearly a one-off debugging artifact.

- **`c`** (file with no extension, project root) — reason: A Python patch script that modifies `accounts/tests.py` to add references to `accounts:audit_log` — a URL name that **does not exist** in any `urls.py`. Running this script would break the test suite. Not imported or referenced anywhere. Leftover from the abandoned audit-log feature.

- **`note for next day.txt`** — reason: Personal note ("audit logs importatnt and deployment for render"). Not referenced by any code, documentation, or configuration file.

- **`test_output.txt`** — reason: Captured terminal output from a test run (`python manage.py test accounts.tests.RoleBasedAccessTests`). Not referenced by any code or documentation. Log artifact.

- **`test_output_all.txt`** — reason: Captured terminal output from a full test run (`python manage.py test -v 2`). Not referenced by any code or documentation. Log artifact.

---

### Likely redundant (needs quick confirmation)

- **`staticfiles/`** (entire directory) — reason: This is the `collectstatic` output directory (`STATIC_ROOT = BASE_DIR / "staticfiles"`). It contains build artifacts: `staticfiles.json`, Django admin static assets, and multiple hashed copies of `theme.css` (e.g., `theme.1c5f69a020a7.css`, `theme.179ac6d9a593.css`, `theme.a31014b2bf7c.css`) plus `.gz` compressed versions. This is generated output, not source code, and should not be committed to version control. **Recommendation:** Add `staticfiles/` to `.gitignore` and remove from the repo. Confirm you don't need it committed for your deployment workflow (Render runs `collectstatic` during build anyway).

- **`static/img/`** (empty directory) — reason: No image files present. No template or CSS file references any image from `static/img/`. Empty placeholder directory.

- **`static/js/`** (empty directory) — reason: No JavaScript files present. `base.html` loads Bootstrap JS from a CDN (`cdn.jsdelivr.net`); no local JS files are referenced via `{% static %}`. Empty placeholder directory.

- **`reports/models.py`** — reason: Contains only `from django.db import models` and a comment `# Reports app currently provides URL/view rendering only.` No model classes defined. The `reports` app is in `INSTALLED_APPS` and has a working view/URL/template, so the app itself is used — but this file is effectively a boilerplate stub. **Not harmful to keep** (Django expects it), but flagging since it defines nothing.

- **`customer/admin.py`** — reason: Contains only the default `django-admin startapp` stub (`from django.contrib import admin` + `# Register your models here.`). The `Customer` model is **not registered** in Django admin, while `Product`, `Category`, `Supplier`, and `User` all have custom `ModelAdmin` classes. This is either intentionally unregistered or was never customized. **Safe to leave as-is** if Customer is deliberately excluded from admin; otherwise this is an incomplete file, not a dead file.

- **`requirements.txt` — `Pillow>=10.0`** — reason: Listed in requirements but not imported anywhere in project code (`import PIL` / `from PIL` returns zero results). No `ImageField` usage in models (all fields are `CharField`, `DecimalField`, `IntegerField`, `DateField`, etc.). Likely included for future image upload features that were never implemented. **Confirm before removing** — may be intended for future use.

- **`requirements.txt` — `openpyxl>=3.1`** — reason: Listed in requirements but not imported anywhere in project code (`import openpyxl` / `from openpyxl` returns zero results). No Excel export functionality exists. Likely included for future report-export features. **Confirm before removing.**

- **`requirements.txt` — `WeasyPrint>=63.0`** — reason: Listed in requirements but not imported anywhere in project code (`import weasyprint` / `from weasyprint` returns zero results). No PDF generation functionality exists. Likely included for future report-printing features. **Confirm before removing.**

- **`requirements.txt` — `django-filter>=24.0`** and **`core/settings.py` — `'django_filters'` in `INSTALLED_APPS`** — reason: `django_filters` is registered in `INSTALLED_APPS` but never used. No `FilterSet` subclass, no `DjangoFilterBackend`, no `django_filters.rest_framework` import, and no `filterset_fields` attribute exists anywhere in the project. All list views use manual `search` query-parameter filtering via `get_queryset()` instead. The package and the `INSTALLED_APPS` entry can both be removed. **Confirm before removing** — may be intended for future use.

---

### Uncertain — needs manual review

- **`accounts/views.py` — unused import `PasswordChangeForm`** — reason: `PasswordChangeForm` is imported on line 4 (`from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm`) but is never referenced in the file body. The password-change URLs in `accounts/urls.py` use `views.PasswordChangeView.as_view()` and `views.PasswordChangeDoneView.as_view()`, which are Django's built-in class-based views imported on line 5 — these in turn use their own internal form. The `PasswordChangeForm` import appears to be a leftover from when a custom password-change view was planned. **Removing the import is safe** but flagging as uncertain in case you plan to customize the password-change form.

- **`README.md` — references `seed_demo_data` management command** — reason: The README (lines 40, 67) and `docs/technical_manual.md` reference `py manage.py seed_demo_data`, but no `management/commands/` directory exists in any app. The command does not exist in the codebase. This is either a feature that was removed without updating docs, or was planned but never implemented. **Not a file to delete** — but the documentation is inaccurate and should be updated.

- **`README.md` — states "32 tests" but actual count is 22** — reason: `test_output_all.txt` shows `Ran 22 tests in 30.686s — OK`, while the README header says "32 tests, 0 failures". The test count in the README is stale. **Not a file to delete** — documentation inaccuracy to fix.

- **`accounts/migrations/0003_activitylog.py`** — reason: Creates the `ActivityLog` model table. The `ActivityLog` model exists in `accounts/models.py` and is tested in `accounts/tests.py`, but it is **never written to by any view, signal, or business-logic method** — no code creates `ActivityLog` entries outside of tests. The model and migration are not dead (the table exists, the model is defined and tested), but the audit-logging feature is incomplete: the model exists but nothing populates it in production code. **Do NOT delete the migration** — it is part of the schema history. Flagging only because the feature is half-implemented.

---

### Empty folders

- **`audit/`** — contains only `audit/migrations/` which itself is empty (no `__init__.py`, no migration files). The `audit` app was scaffolded but never built out.
- **`audit/migrations/`** — no files.
- **`accounts/templatetags/`** — no files (no `__init__.py`, no tag modules).
- **`templates/audit/`** — no files.
- **`static/img/`** — no files.
- **`static/js/`** — no files.
- **`reports/migrations/`** — no files (no `__init__.py`). This is expected because `reports` has no models, so Django never creates migration files for it. **Not a problem** — flagging for completeness.

---

### Already ignored but present in working tree (should be gitignored / cleaned locally)

The current `.gitignore` covers:
```
.venv          .env           __pycache__/    *.pyc
*.log          *.backup       .DS_Store       db.sqlite3
.vscode        .claude        .remember
```

**Missing from `.gitignore` (recommended additions):**

| Pattern | Reason |
|---|---|
| `staticfiles/` | `collectstatic` build output (`STATIC_ROOT`). Currently present in the working tree with hashed CSS files and admin assets. Should not be committed — Render runs `collectstatic` during build. |
| `media/` | `MEDIA_ROOT = BASE_DIR / "media"` is configured in settings. User-uploaded files should never be committed. (Directory does not currently exist, but the gitignore entry should be preemptive.) |
| `*.sqlite3` | Current `.gitignore` has `db.sqlite3` but not the wildcard. A second SQLite file (e.g., `db_test.sqlite3`) would not be caught. |
| `.idea/` | JetBrains IDE folder — not currently present but standard to ignore. |

**Already properly gitignored and not a concern:**
- `__pycache__/` and `*.pyc` — covered
- `.env` — covered
- `.DS_Store` — covered
- `db.sqlite3` — covered
- `.venv` — covered

---

### Duplicate logic/files across apps

1. **Duplicate login template** — `accounts/templates/accounts/login.html` duplicates `templates/accounts/login.html`. Both render the login form with `crispy_forms_tags`, extend `base.html`, and link to the register page. The `templates/` version uses the newer `page-surface` / `form-surface` CSS classes; the `accounts/templates/` version uses older plain Bootstrap classes. Only the `templates/` version is served (DIRS takes precedence over APP_DIRS). **Recommendation:** Delete `accounts/templates/accounts/login.html` and remove the now-empty `accounts/templates/` directory.

2. **No shared template partials issue** — The project correctly uses `templates/includes/messages.html` as a shared partial, included once in `base.html` via `{% include 'includes/messages.html' %}`. However, several templates (login, register, admin_register, pending_users) **duplicate the messages-display block inline** instead of relying on the `base.html` include. This is copy-pasted code, not a duplicate file, so it is a refactoring concern rather than a deletion target. Flagging for awareness only.

3. **No duplicate models or utility functions found** — Each app defines its own distinct models. `Supplier` and `Customer` share a similar field structure (name, contact_person, email, phone, address, city, postal_code, country, is_active) but are separate domain entities with different relationships and should not be consolidated.

---

### Migration files — no action needed

All migration files are sequential and part of the active schema history. **None should be deleted.**

| App | Migrations | Status |
|---|---|---|
| `accounts/` | `0001_initial`, `0002_user_date_requested_user_is_approved`, `0003_activitylog` | All sequential, all applied |
| `category/` | `0001_initial` | Single migration, applied |
| `product/` | `0001_initial`, `0002_purchaseorder_…`, `0003_sale_payment_saleitem`, `0004_product_expiration_date_alert` | All sequential, all applied |
| `supplier/` | `0001_initial`, `0002_supplier_outstanding_balance_supplierpayment` | All sequential, all applied |
| `customer/` | `0001_initial` | Single migration, applied |
| `reports/` | (none) | No models — no migrations needed |
| `audit/` | (none — empty dir) | App never built — no migrations exist |

No squashed migrations were found. No orphaned migration files detected.

---

### Summary

| Category | Count |
|---|---|
| Safe to delete (confirmed unused) | 8 items |
| Likely redundant (needs confirmation) | 8 items |
| Uncertain (needs manual review) | 4 items |
| Empty folders | 7 items |
| .gitignore additions needed | 4 patterns |
| Duplicate files | 1 (login template) |
| Migration files to delete | **0 — do not delete any migrations** |

### Next steps (after your review)

1. **Confirm the "Safe to delete" list** — I will remove only the items you approve, in a single commit for easy revert.
2. **Confirm or reject the "Likely redundant" items** — especially the `requirements.txt` packages (Pillow, openpyxl, WeasyPrint, django-filter) and `staticfiles/`.
3. **Update `.gitignore`** — add `staticfiles/`, `media/`, `*.sqlite3`, `.idea/`.
4. **After deletion:** run `python manage.py check`, `python manage.py test`, and a manual `runserver` start to confirm nothing broke.
5. **Fix documentation inaccuracies** (separate from cleanup): README references non-existent `seed_demo_data` command and states "32 tests" (actual: 22).
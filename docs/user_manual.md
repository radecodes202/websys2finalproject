# User Manual

## Roles
The system supports four roles, each with a different set of pages and actions:

| Role | Scope |
|---|---|
| **Admin** | Full administration across all modules; manage users and approvals |
| **Manager** | Inventory, suppliers, customers, reports, and dashboard |
| **Cashier** | Customers and sales (POS), plus the dashboard |
| **Inventory Staff** | Products, categories, suppliers, and the dashboard |

Access is enforced both at the view level (`RoleRequiredMixin`) and in the UI — sidebar links and quick-action buttons only appear for authorized roles.

## Getting Started
1. Open the app in a browser and go to `/accounts/login/`.
2. Log in with your assigned account (see the demo accounts in the README).
3. After signing in you land on the **Dashboard**.

## Authentication & Account Approval
- New users can **self-register** at `/accounts/register/`. These accounts are created as **pending** and **cannot log in** until an admin approves them.
- An **admin** approves pending accounts from **Dashboard → Pending Users**. Once approved, the user can sign in.
- **Admins** can also register users directly (including other admins) at `/accounts/admin/register/`. Users created here are approved immediately — bypassing the pending workflow.
- Use **Password change** (`/accounts/password_change/`) to update your own password.

## Dashboard
The dashboard shows four summary cards:
- **Total Products** — number of active products
- **Total Sales Today** — sales completed today
- **Low Stock Items** — products at or below their reorder level
- **Open Alerts** — unresolved low-stock / expiring / expired alerts

The sidebar and quick-action buttons are role-aware, so you only see links you're allowed to use.

## Common Tasks
1. Log in to the system.
2. Review the dashboard summary cards.
3. Manage **categories**, **products**, **suppliers**, and **customers** from their list screens (use the search box, then Create / Update / Delete).
4. As an **admin**, review **Pending Users** and approve new registrations.
5. As an **admin** or **manager**, open **Reports → Sales** to review the list of sales with their line items and payments.

## Page Access by Role
See the "Web Interface (Pages)" table in the README for the full breakdown. In short:
- **Categories, Products, Suppliers** — admin, manager, inventory staff
- **Customers** — admin, manager, cashier
- **Reports** — admin, manager
- **Pending Users / Admin Registration** — admin only
- **Dashboard** — all authenticated users

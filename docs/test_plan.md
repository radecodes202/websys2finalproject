# Test Plan

## Current Regression Coverage
- Auth and dashboard flow
- Category, product, supplier, and customer CRUD
- Purchase order and stock receipt flow
- Sales and payment processing
- Supplier payment tracking
- Activity log creation
- Browser security defaults

## Execution Commands
- `py manage.py test accounts.tests`
- `py manage.py test accounts.tests product.tests supplier.tests customer.tests category.tests`

## Expected Results
All listed regression suites should complete with status `OK`.

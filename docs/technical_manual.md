# Technical Manual

## Project Overview
This repository is a Django-based inventory, sales, and supplier management system designed for small business operations.

## Setup
1. Create a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env` and adjust values.
4. Run `py manage.py migrate`.
5. Run `py manage.py seed_demo_data` to load demo data.
6. Start the app with `py manage.py runserver`.

## Architecture
- `accounts`: authentication, role model, audit trail
- `category`: product categorization
- `product`: inventory, purchases, sales, alerts, and stock movement logic
- `supplier`: supplier master data and payment tracking
- `customer`: customer records
- `reports`: report entry points

## Deployment Notes
- Use `gunicorn` behind reverse proxy or container host.
- Serve static assets with `whitenoise`.
- Use environment-backed settings for production secrets.

## Render Deployment Checklist
1. Add a Render Web Service pointing at the repository.
2. Set the build command to `pip install -r requirements.txt && python manage.py collectstatic --noinput`.
3. Set the start command to `gunicorn core.wsgi:application`.
4. Add a Postgres database service and wire the connection variables through `.env`-style Render environment settings.
5. Confirm the `ALLOWED_HOSTS` value includes the Render domain.

## Backup Strategy
Use a scheduled database dump process such as `pg_dump` or `mysqldump` and restore with the matching toolchain.

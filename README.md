# Hostel Management System

Custom Django hostel cot booking and rent management system with:

- Dynamic hostel setup: area, building, section, floor, room, cot
- Public student cot browsing and booking flow
- Custom Mifty-based admin panel at `/panel/`
- Django admin backup at `/django-admin/`
- PostgreSQL-required configuration with environment variables
- QR payment upload, manual verification, and WhatsApp logging
- Monthly billing, grace-period handling, and future-ready access control

## Project Structure

```text
config/
apps/
  accounts/
  hostel/
  bookings/
  payments/
  whatsapp/
  reports/
  access_control/
templates/
  layouts/
  admin_panel/
  public/
static/
  mifty/
  public/
media/
```

## Mifty Template Note

The original pasted `assets/` or Mifty reference folder is only needed while building.  
Runtime assets are copied into `static/mifty/`, so the raw reference folders can be removed later if you want.

## Installation

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set:

- `SECRET_KEY`
- `DEBUG`
- `REQUIRE_POSTGRESQL=True`
- `ALLOWED_HOSTS`
- `DATABASE_URL` or the individual `DB_*` values
- `PANEL_ADMIN_EMAIL`
- `PANEL_ADMIN_USERNAME`
- `PANEL_ADMIN_PASSWORD`

## PostgreSQL Setup

PostgreSQL is mandatory for this project. SQLite fallback is disabled by default.

Create a PostgreSQL database named `hostel_management` or update `.env` with your preferred database name.

Example:

```text
REQUIRE_POSTGRESQL=True
DATABASE_URL=postgresql://postgres:password@127.0.0.1:5432/hostel_management
```

If PostgreSQL is not configured, Django will stop at startup with a settings error.

## Django Commands

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py ensure_panel_admin
python manage.py createsuperuser
python manage.py collectstatic
python manage.py runserver
```

## Admin Routes

- `/panel/login/`
- `/panel/dashboard/`
- `/panel/areas/`
- `/panel/buildings/`
- `/panel/sections/`
- `/panel/floors/`
- `/panel/rooms/`
- `/panel/cots/`
- `/panel/bookings/`
- `/panel/payments/`
- `/panel/qr-settings/`
- `/panel/whatsapp/`
- `/panel/reports/`
- `/panel/settings/`

## Public Flow

1. Open `/`
2. Choose area
3. Choose building
4. Choose section
5. Choose floor
6. Choose room
7. Choose cot
8. Submit student booking and QR payment proof

## Management Commands

Generate current month bills:

```bash
python manage.py generate_monthly_bills
```

Update gate / thumb access status based on billing:

```bash
python manage.py update_access_status
```

Create or refresh the default panel admin from environment variables:

```bash
python manage.py ensure_panel_admin
```

## Features Included

- Dynamic hostel hierarchy management
- Cot pricing and security deposit control
- Excel bulk upload with reuse and update rules
- Student document upload
- Booking verification workflow
- QR payment settings
- Monthly rent billing and partial first-month calculation
- Grace period extension
- Student ledger
- Access control models and logs
- WhatsApp provider-ready service layer and logs
- Excel export for reports

## Render Deployment Notes

1. Push the project to GitHub.
2. Create a Render Web Service.
3. Set the build command:

```bash
pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
```

4. Set the start command:

```bash
gunicorn config.wsgi --log-file -
```

5. Set environment variables:

- `SECRET_KEY`
- `DEBUG=false`
- `DATABASE_URL=<render-postgres-url>`
- `PANEL_ADMIN_EMAIL=admin@example.com`
- `PANEL_ADMIN_USERNAME=admin@example.com`
- `PANEL_ADMIN_PASSWORD=<your-admin-password>`

## VPS Deployment Notes

Recommended stack:

- Ubuntu VPS
- Python virtual environment
- PostgreSQL
- Gunicorn
- Nginx

Typical flow:

```bash
git clone <repo>
cd <project>
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```

Then configure:

- Gunicorn as a systemd service
- Nginx reverse proxy to Gunicorn
- Media and static handling
- Environment variables in a secure `.env`

## Important Notes

- `static/mifty/` is the runtime admin UI asset directory.
- `media/` stores student photos, proof images, QR images, and screenshots.
- Django admin is kept only as a backup for superuser/developer usage.
- Billing and booking logic are separated into service functions.
- Access control is future-ready for biometric hardware integration.

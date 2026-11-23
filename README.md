# handEwork

handEwork is a skilled-work marketplace for Ghana and other African markets. Customers can find verified artisans by service, location and availability, agree a job, communicate, fund it through mobile money and keep the work record in one place. Artisans receive a public work profile, scheduling, bookings, portfolio, verification, earnings and business tools.

Tagline: **Powering Everyday Work**
Brand line: **Built for the Hands that Build**

## What is in this release

- `app/` — responsive web marketplace and operational workspaces
- `backend/` — Flask API, MySQL models and migrations, payments, escrow ledger, chat, notifications and workers
- `mobile/` — Expo React Native client for Android and iOS
- `docs/` — Windows setup, provider configuration, deployment, security and API manuals
- `render.yaml` — Render Blueprint for web, API, worker and Redis-compatible Key Value
- `docker-compose.yml` — local MySQL 8.4 and Redis
- `.github/workflows/ci.yml` — web build, backend tests/migration and mobile typecheck

No test users, fake artisans, sample balances or placeholder transactions are included. Public service categories are taxonomy, not marketplace records. Search results come only from approved artisan rows in the connected database.

## Start here

1. Read [`docs/WINDOWS_LOCAL_SETUP.md`](docs/WINDOWS_LOCAL_SETUP.md).
2. Copy `.env.example`, `backend/.env.example` and `mobile/.env.example` to their local `.env` files.
3. Start MySQL and Redis: `docker compose up -d mysql redis`.
4. Run the database migration and Flask API.
5. Run the web application.
6. Create an Expo development build for mobile testing. Mapbox and push notifications require a development build, not Expo Go.

For web deployment, browser installation, and homepage animations, see [Deploy handEwork on Vercel](VERCEL.md).

## Verification commands

```powershell
# Web
npm ci
npm run lint
npm run build

# API
Set-Location backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
flask --app wsgi:app db upgrade

# Mobile
Set-Location ..\mobile
npm ci
npm run typecheck
```

## Release boundary

The application code and provider adapters are implemented. Production activation still requires the owner-controlled items that cannot be embedded in source: provider-approved accounts, live secrets, a MySQL service, object storage, DNS, Paystack webhook registration, app-store accounts, legal approval and real artisan verification. The exact steps are in `docs/EXTERNAL_INTEGRATIONS.md` and `docs/DEPLOY_GITHUB_RENDER.md`.

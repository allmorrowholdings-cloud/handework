# handEwork release manifest

Release date: 15 August 2026

## Web routes

Public and access: `/`, `/marketplace`, `/how-it-works`, `/safety`, `/about`, `/business`, `/training`, `/support`, `/legal/privacy`, `/legal/terms`, `/auth/sign-in`, `/auth/create-account`, `/join/artisan`, `/artisan/pro`.

Customer: `/dashboard`, `/bookings`, `/bookings/new`, `/bookings/:id`, `/messages`, `/messages/:id`, `/wallet`, `/notifications`, `/referrals`, `/disputes`, `/settings`.

Artisan: `/artisan/dashboard`, `/artisan/profile`, `/artisan/availability`, `/artisan/portfolio`, `/artisan/verification`.

Administration: `/admin` and `/admin/:section` for API-backed operations queues.

## Mobile routes

Welcome, sign-in, customer registration, artisan registration, customer home, search with GPS/Mapbox, bookings, booking request, booking record, mobile-money initiation, chat and image attachment, wallet, messages, account, notifications, disputes, artisan workboard, profile, availability, portfolio and verification.

## Server modules

- Account and role security
- Artisan search and distance
- Booking state machine and quotes
- Paystack Ghana mobile money
- Signed payment webhooks
- Wallet and ledger
- Release and refund boundaries
- REST and Socket.IO chat
- S3-compatible uploads
- Notifications and Celery worker
- Reviews, referrals, promos and subscriptions
- Organizations and training providers
- KYC, disputes, risk and audit logs
- Administrator analytics and queues

## Verification recorded for this release

- Web lint: passed
- Web production build: passed
- Backend compile: passed
- Backend migration upgrade: passed
- Backend automated tests: 17 passed
- Backend line coverage: 78%
- Mobile TypeScript: passed

External provider end-to-end tests are not claimed in this manifest. They require the owner’s live or sandbox accounts and are listed in `docs/EXTERNAL_INTEGRATIONS.md`.

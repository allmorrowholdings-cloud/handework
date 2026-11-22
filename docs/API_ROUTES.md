# handEwork API routes

Base path: `/v1`

Authentication uses `Authorization: Bearer ACCESS_TOKEN`. Payment creation also requires `Idempotency-Key`.

## Public and account

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/health` | API and database health |
| POST | `/auth/register` | Customer account |
| POST | `/auth/register-artisan` | Artisan account and draft profile |
| POST | `/auth/login` | Access and refresh tokens |
| POST | `/auth/refresh` | Replace expired access token |
| GET/PATCH | `/auth/me` | Current account, contact and notification preferences |

## Marketplace and artisans

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/artisans/search` | Verified available artisan search |
| GET | `/artisans/:id` | Public profile and approved portfolio |
| GET/PATCH | `/artisans/me` | Own artisan profile |
| GET/PUT | `/artisans/me/availability` | Weekly hours |
| GET/POST | `/artisans/me/portfolio` | Own portfolio and upload |
| GET/POST | `/artisans/me/verifications` | Private KYC checks and payout name |

Search parameters:

- `service`
- `coordinates=latitude,longitude`
- `location` for server geocoding
- `distance_km`, capped at 100
- `date=YYYY-MM-DD` for weekly availability matching

## Bookings and quotes

| Method | Route | Purpose |
| --- | --- | --- |
| GET/POST | `/bookings` | List jobs or create a request/eligible instant booking |
| GET | `/bookings/:id` | Job and status history |
| POST | `/bookings/:id/quotes` | Artisan quote |
| POST | `/bookings/:id/quotes/:quoteId/accept` | Customer accepts quote |
| POST | `/bookings/:id/status` | Valid state transition |
| POST | `/bookings/:id/release` | Customer/admin release after completion submission |

## Payments and wallet

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/payments/mobile-money` | Paystack Ghana mobile-money charge |
| POST | `/webhooks/paystack` | Signed provider events |
| POST | `/payments/:id/refund` | Administrator refund request |
| GET | `/wallet` | Currency balances |
| GET | `/wallet/transactions` | Ledger entries |

## Chat, files and notifications

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/conversations` | Participant threads |
| GET/POST | `/conversations/:id/messages` | Read or send messages |
| PATCH | `/messages/:id` | Edit own message |
| POST | `/uploads` | Purpose-tagged private file |
| GET/PATCH | `/notifications` | Read and mark notifications |
| POST | `/push-devices` | Register Expo push token |

Socket.IO event: `join.conversation`. Server event: `message.created`.

## Reviews, disputes and commercial tools

| Method | Route | Purpose |
| --- | --- | --- |
| GET/POST | `/disputes` | List or open participant dispute |
| POST | `/reviews` | Customer review for completed booking |
| GET | `/referrals` | Referral code and qualification records |
| POST | `/promo-codes/validate` | Validate promotion against amount and rules |
| POST | `/subscriptions` | Create pending handEwork Pro subscription record |
| GET | `/training/courses` | Published verified courses |
| GET/POST | `/organizations` | Company accounts and membership |
| POST | `/support` | Authenticated or public support ticket |

## Administrator

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/admin/queue` | Combined operational queue |
| GET | `/admin/verifications` | KYC queue |
| POST | `/admin/verifications/:id/decision` | KYC decision and audit |
| GET | `/admin/disputes` | Dispute queue |
| POST | `/admin/disputes/:id/decision` | Resolution record and audit |
| GET | `/admin/payments` | Payment exceptions |
| GET | `/admin/risk` | Risk queue |
| POST | `/admin/risk/:id/decision` | Risk decision and audit |
| GET | `/admin/analytics` | Period totals |

## Error format

```json
{
  "message": "Human-readable message",
  "code": "stable_machine_code"
}
```

Clients must not decide authorization or payment success from UI state. They render the server result.

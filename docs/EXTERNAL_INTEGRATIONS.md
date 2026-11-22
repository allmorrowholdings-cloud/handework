# External integrations and manual configuration

The code reads integration values from environment variables. Keep live values in Render, EAS and your private password manager. Never commit `.env`.

## 1. Paystack: MTN MoMo, Telecel Cash and ATMoney

The API uses Paystack Ghana mobile-money charges.

Provider codes used by Paystack:

| Customer network | Paystack code |
| --- | --- |
| MTN | `mtn` |
| Telecel | `vod` |
| ATMoney / AirtelTigo | `atl` |

### Configure

1. Complete Paystack business verification for Ghana.
2. Start with the Paystack test secret key.
3. Set `PAYSTACK_SECRET_KEY` on the API and worker.
4. Set `PAYSTACK_BASE_URL=https://api.paystack.co`.
5. Deploy the API.
6. In Paystack Dashboard, set the webhook URL to:

   `https://YOUR-API-DOMAIN/v1/webhooks/paystack`

7. Confirm the endpoint receives `charge.success` in test mode.
8. Confirm one provider reference maps to one handEwork payment.
9. Confirm the booking changes from `accepted` to `funded` only after the signed webhook.
10. Confirm the wallet ledger records the held amount.
11. Run a refund in test mode and confirm `refund.processed` updates the payment.
12. Switch to the live secret only after reconciliation tests pass.

The official channel reference is: https://paystack.com/docs/payments/payment-channels/

### Escrow wording

The code implements held and available wallet buckets. Get Ghana-qualified legal and payment advice before marketing handEwork as a regulated escrow service. Confirm the settlement account, chargeback responsibility, refund timing, artisan payout timing, platform fee and unclaimed balance treatment.

## 2. Mapbox

Use separate public and server tokens.

### Web and mobile public token

1. Create a public Mapbox token.
2. Restrict its URLs for web after the final domain is known.
3. Set `NEXT_PUBLIC_MAPBOX_TOKEN` for web.
4. Set `EXPO_PUBLIC_MAPBOX_TOKEN` for mobile.
5. Keep the Mapbox wordmark and attribution visible.

### Mobile SDK download token

1. Create a secret token with the SDK download scope required by Mapbox.
2. Store it as the EAS secret `RNMAPBOX_MAPS_DOWNLOAD_TOKEN`.
3. Do not expose this token through an `EXPO_PUBLIC_` variable.

### Server token

1. Create a token for server geocoding and directions.
2. Set `MAPBOX_SECRET_TOKEN` only on the Flask API.
3. Test a Ghana address and compare the returned coordinates with the expected place.
4. Test route distance separately from straight-line distance.

Mapbox token guidance: https://docs.mapbox.com/help/dive-deeper/access-tokens/

## 3. Object storage for portfolios, chat and job evidence

The backend uses an S3-compatible API.

1. Create a private bucket.
2. Create a service identity limited to that bucket.
3. Allow `PutObject`, `GetObject` and the deletion operations required by the retention policy.
4. Require server-side encryption.
5. Block public bucket listing.
6. Set:

   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION`
   - `S3_BUCKET`
   - `S3_PUBLIC_BASE_URL` only if you intentionally serve approved public portfolio media through a CDN

7. Keep identity files private. Do not use a public base URL for KYC.
8. Add malware scanning before changing `FileAsset.scan_status` from `pending`.
9. Apply retention rules by purpose: chat evidence, job evidence, portfolio, support and KYC should not share one automatic deletion period.
10. Test deletion against a non-production file.

## 4. Hubtel SMS

1. Create or use a Hubtel business account.
2. Request and approve the handEwork sender ID.
3. Set `HUBTEL_CLIENT_ID`, `HUBTEL_CLIENT_SECRET` and `HUBTEL_SENDER_ID=handEwork` on API and worker.
4. Use SMS for time-sensitive events only: verification codes, booking acceptance, arrival, payment status and dispute decisions.
5. Record delivery results and retry temporary failures through Celery.
6. Test Ghana numbers in E.164 format, such as `+233...`.

## 5. WhatsApp

WhatsApp requires a provider account and approved templates.

1. Choose Meta WhatsApp Cloud API or an approved business provider.
2. Verify the handEwork business and sending number.
3. Create templates for booking accepted, artisan en route, payment confirmed, completion submitted and support update.
4. Set the provider URL and token through `WHATSAPP_PROVIDER_URL` and `WHATSAPP_PROVIDER_TOKEN`.
5. Set the provider message endpoint and bearer token. The included worker sends the Meta-compatible text payload through `send_whatsapp`.
6. Store consent. Do not subscribe every account automatically.
7. Provide an opt-out route and respect it before queueing a message.

The provider-neutral boundary is deliberate because no WhatsApp vendor was named in the project environment.

## 6. Expo push, FCM and APNs

1. Create the EAS project:

   `npx eas-cli@latest init`

2. Put the returned ID in `mobile/app.json` at `expo.extra.eas.projectId`.
3. Configure Android FCM v1 credentials in EAS.
4. Configure Apple APNs credentials and the Push Notifications capability.
5. Set `EXPO_ACCESS_TOKEN` on the worker if access-token security is enabled.
6. Build a development client. Push is not tested through Expo Go.
7. In the mobile Account screen, enable push notifications.
8. Confirm the Expo token is stored by `POST /v1/push-devices`.
9. Send a test job notification.
10. Process delivery receipts and deactivate invalid tokens before public scale.

Expo guide: https://docs.expo.dev/push-notifications/push-notifications-setup/

## 7. MySQL 8

1. Use MySQL 8.4 locally from `docker-compose.yml`.
2. Create a private production MySQL service with persistent storage and daily backups.
3. Use a dedicated `handework` database and application user.
4. Do not use the MySQL root account from Flask.
5. URL-encode special password characters in `DATABASE_URL`.
6. Use the format:

   `mysql+pymysql://USER:PASSWORD@HOST:3306/handework`

7. Run `flask --app wsgi:app db upgrade` before the new API version receives traffic.
8. Test a backup restore into a separate database.
9. Set an alert for failed backups, disk growth and connection exhaustion.

Render MySQL guide: https://render.com/docs/deploy-mysql

## 8. Redis and Celery

1. The Render Blueprint creates a private Key Value instance.
2. It passes the internal connection string as `REDIS_URL` to API and worker.
3. Confirm the `handework-worker` service is running.
4. Queue a notification and confirm the worker changes it from `queued` to `sent`.
5. Monitor retry count and dead tasks.
6. Paid jobs, refunds and KYC decisions must never depend on an unmonitored background task.

## 9. Identity verification

The schema supports `government_id`, `live_selfie`, `trade_proof` and `payout_name` checks.

Choose one operating method before launch:

- Manual review by trained handEwork staff, or
- A contracted Ghana-capable KYC provider plus manual exceptions.

Required manual rules:

1. Define accepted documents.
2. Define selfie/liveness rules.
3. Require payout ownership to match identity.
4. Record rejection reasons without exposing internal fraud methods.
5. Set retention and deletion periods.
6. Restrict reviewers by administrator role.
7. Audit every approval and rejection.
8. Provide an appeal route.

## 10. AI matching

The production matcher is safe without a model. Deterministic rules control verification, availability, distance and risk. An AI similarity value may contribute only to service-text fit.

Before enabling a model:

1. Build an anonymized set of real search phrases and correct service categories.
2. Measure precision by category and language.
3. Test Twi, Ga and Ghanaian English terms.
4. Keep safety and distance filters outside the model.
5. Store the model name and version with matching logs.
6. Add a fallback to deterministic category matching.
7. Do not send KYC images, exact home addresses, payment details or private chat into the matching model.
8. Set `AI_MATCHING_API_KEY` and `AI_MATCHING_MODEL` only after the evaluation passes.

## 11. Error monitoring

1. Create separate web, API and mobile projects in your monitoring provider.
2. Set `SENTRY_DSN` for API and `EXPO_PUBLIC_SENTRY_DSN` for mobile only after the SDK is installed and privacy settings are approved.
3. Remove message bodies, KYC fields, tokens, phone numbers and exact addresses from error payloads.
4. Alert on API 5xx, webhook failures, worker failures, ledger mismatches and mobile crash-free rate.

## 12. Final provider test sequence

Run this order in a non-production environment:

1. Customer and artisan account creation.
2. Artisan KYC upload and administrator approval.
3. Availability, location and portfolio.
4. GPS search and route distance.
5. Booking, quote and acceptance.
6. Customer–artisan chat and image upload.
7. Paystack test mobile-money charge.
8. Signed webhook and escrow ledger entry.
9. Job status and before/after photo.
10. Completion approval and release.
11. Refund and dispute paths.
12. SMS, WhatsApp and push.
13. Administrator audit record.
14. Backup and restore.

Do not switch a provider to live mode until its part of this sequence passes.

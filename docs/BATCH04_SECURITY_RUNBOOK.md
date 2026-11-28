# handEwork — Batch 04 Security & Production Readiness

## Scope and status
This patch hardens JWT session revocation and backend security headers; it adds focused regression tests and a safe production-configuration checker. It **does not** mean every subsystem has been penetration-tested or live-certified. The mobile/web workspace release is already on `main` at `579ec446`.

## Production readiness gates — mandatory before sign-off

1. **Render API:** Confirm the deployed commit, `/v1/health` HTTP 200, database connectivity, Redis connectivity, runtime logs and error monitoring. The checker reports configuration presence, not provider connectivity. Do not share token or secret values.
2. **OTP/Arkesel:** Confirm `PHONE_OTP_ENABLED`, `SMS_ENABLED`, `SMS_PROVIDER`, `ARKESEL_API_KEY`, `ARKESEL_SENDER_ID`, `REDIS_URL` and `SECRET_KEY` on Render, then send a real OTP to a test-owned Ghana phone; confirm expiration, resend cooldown, wrong-code lockout, phone-change invalidation, and successful user verification. Never copy OTPs into logs or chat. `ARKESEL_OTP_API_KEY` is not used by the current local Redis/HMAC OTP transport.
3. **Google web/PWA:** Verify the correct frontend `NEXT_PUBLIC_GOOGLE_CLIENT_ID` and server `GOOGLE_CLIENT_ID`, OAuth-origin configuration, Google sign-in, Google account linking, MFA, and customer/artisan/admin redirects in actual browsers. The Google-rendered button is an external iframe; styling its interior cannot be guaranteed from application CSS. Capture a screenshot of any remaining white-square problem.
4. **Android APK:** Expo Android configuration still includes a placeholder EAS project ID. Configure the real EAS project with the owner's Expo credentials before an actual Android build; validate Home/Activities/Account for each role and real permissions/notifications on a device. Mobile CI TypeScript checks are not APK tests.
5. **Paystack/financial controls:** Inspect callback/webhook HMAC checks, duplicated callback replay, idempotency and reconciliation with provider sandbox accounts; do not test live payments unintentionally. The scheduled Payment reconciliation workflow being `skipped` when disabled is **not** failed CI.
6. **WorkProof and identity:** Check uploads and evidence signed URLs for access by other users and admin-only review changes; verify no arbitrary role escalation.
7. **Security operations:** Verify admin TOTP policy, logs without secrets, Sentry scrubbing, incident escalation, DB backup and restore rehearsal, and rollback playbook.

## Safe Render shell check

`python backend/scripts/production_readiness.py`

Run from repository root within a shell containing **Render environment variables**. It prints only pass/check status and never changes configuration. The frontend-only `NEXT_PUBLIC_GOOGLE_CLIENT_ID` may be absent from Render even if correctly configured in Vercel; verify it there instead.

## Release rules
- Open one security PR, run web/API/mobile CI and inspect changed file list.
- Do not enable payment or SMS feature flags merely to make readiness report pass.
- Do not promise full APK, OTP delivery, or Render runtime validation until actual live tests.
- Keep the original local stash separate from the new security branch.

# handEwork security and launch gates

Public launch is blocked until every P0 item is checked by the named owner.

## P0: identity and access

- [ ] Live `SECRET_KEY` and `JWT_SECRET_KEY` are different, random and stored outside Git.
- [ ] Administrator accounts use unique passwords and limited membership.
- [ ] Administrator route checks are tested against customer and artisan tokens.
- [ ] Suspended users cannot sign in or use a refresh token.
- [ ] Web refresh tokens are moved from browser storage to Secure, HttpOnly, SameSite cookies before broad public scale.
- [ ] Mobile tokens stay in SecureStore.
- [ ] Password reset and email/phone verification are implemented through single-use, expiring server tokens before relying on verified contact claims.
- [ ] No identity document URL is public.

## P0: payments and ledger

- [ ] Paystack live webhook URL is correct.
- [ ] Invalid signatures return `401`.
- [ ] Repeated success events do not duplicate ledger entries.
- [ ] Idempotency keys are required on charge requests.
- [ ] Amounts are compared in the expected currency and smallest unit.
- [ ] A booking cannot fund twice.
- [ ] A customer cannot release before completion submission.
- [ ] A disputed booking stops automatic release.
- [ ] Refunds are reconciled against provider events.
- [ ] Held and available balances reconcile to ledger entries daily.
- [ ] Platform-fee tax and settlement treatment is approved.
- [ ] “Escrow” wording is approved by Ghana-qualified advisers and the payment provider.

## P0: booking and safety

- [ ] Every status change passes the server transition map.
- [ ] Customer and artisan access is tested against another user’s booking ID.
- [ ] Chat access is limited to booking participants and administrators.
- [ ] Exact home addresses are never shown in public search.
- [ ] Emergency language and local reporting instructions are approved.
- [ ] A safety issue receives an urgent support priority.
- [ ] Administrator dispute decisions write an audit entry.
- [ ] Refund/release financial action remains separate from the support note.

## P0: files and KYC

- [ ] Upload size and MIME allow-list are active.
- [ ] Object storage uses server-side encryption.
- [ ] Bucket listing and anonymous writes are blocked.
- [ ] Malware scanning changes `scan_status` before staff or users open attachments.
- [ ] KYC, chat evidence, booking photos and public portfolio have different access rules.
- [ ] KYC retention and deletion are approved.
- [ ] Portfolio ownership and permission language is shown before upload.
- [ ] Reviewer access and KYC appeal are documented.

## P0: infrastructure

- [ ] MySQL is private and uses a non-root application user.
- [ ] MySQL persistent disk and daily backup are active.
- [ ] A backup restore succeeds into a separate database.
- [ ] Redis is private.
- [ ] API and worker share the correct database, Redis and secret values.
- [ ] `/v1/health` reports database `ok`.
- [ ] Migrations run before traffic on every schema release.
- [ ] WEB_ORIGINS contains only approved HTTPS origins in production.
- [ ] Rate-limit storage uses Redis, not in-process memory.
- [ ] TLS is active on web and API domains.

## P0: privacy and legal

- [ ] Privacy notice and terms are approved for the operating company.
- [ ] Account deletion exists and explains retained payment/dispute records.
- [ ] Data export is implemented for eligible account, booking and message data.
- [ ] Payment, location, KYC and communication providers are listed in the privacy inventory.
- [ ] Consent exists for optional WhatsApp and marketing communication.
- [ ] Worker classification, consumer protection, tax, refunds and dispute rules are approved.
- [ ] Apple and Google privacy/data-safety answers match actual code.

## P0: operational readiness

- [ ] At least two administrators can cover payment and safety incidents.
- [ ] Payment reconciliation has a daily owner.
- [ ] KYC reviews have a response target and escalation path.
- [ ] Disputes have evidence rules and decision authority.
- [ ] Provider outages have a customer message and retry plan.
- [ ] A severe incident has an owner, internal channel and customer notice process.
- [ ] No demo artisan, balance, review, course or transaction exists in production.

## P1: before expansion

- [ ] Device/session management and remote session revocation.
- [ ] Refresh-token rotation and reuse detection.
- [ ] Dedicated search index when MySQL text search no longer meets latency targets.
- [ ] Route distance caching with privacy-safe keys.
- [ ] Automated KYC provider with manual exceptions.
- [ ] Model evaluation and monitoring for semantic matching.
- [ ] Country policy package for each new market.
- [ ] Multi-currency ledger reconciliation.
- [ ] Business invoicing and approval audit.
- [ ] Data warehouse with consent, retention and access controls.

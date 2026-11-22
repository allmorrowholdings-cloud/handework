# handEwork MVP implementation plan

This plan assumes the current codebase. It does not ask the team to rebuild screens that already exist.

## Stage 0: ownership and accounts

Complete before technical launch work.

1. Confirm the operating company and domain owner.
2. Make Phillipa Aidoo owner or administrator of GitHub, Render, Expo, Apple, Google Play, Paystack, Mapbox, storage, Hubtel and monitoring.
3. Add Christabel Aidoo to design review access without payment or production-secret access unless her role requires it.
4. Put recovery codes and provider ownership in the company password manager.
5. Name the person who can approve refunds, KYC and safety actions.

Exit: no production account depends on one inaccessible personal email.

## Stage 1: local product

1. Run MySQL and Redis.
2. Run the migration.
3. Run web, API and mobile type checks.
4. Create one customer and one artisan locally.
5. Approve the artisan through the administrator route.
6. Set location and availability.
7. Search and create a booking.
8. Quote and accept.
9. Test chat and image upload with a non-sensitive test file.
10. Run the backend test suite.

Exit: the full booking record works without live money.

## Stage 2: provider sandbox

1. Configure Mapbox test tokens.
2. Configure a private development bucket.
3. Configure Paystack test mode and webhook.
4. Configure Redis worker.
5. Create an EAS development build.
6. Configure Android FCM and iOS APNs.
7. Configure an SMS test sender.
8. Run the 14-step provider sequence in `EXTERNAL_INTEGRATIONS.md`.

Exit: payment, webhook, ledger, push and file paths work in non-production.

## Stage 3: controlled Accra pilot

Recommended initial scope:

- Accra only.
- Plumbing, electrical, hair/beauty and tailoring.
- 20–50 manually verified artisans.
- Invite-only customers for the first operating days.
- Human review of each payment exception and dispute.

Manual work:

1. Verify every artisan.
2. Capture accurate service area, travel radius and availability.
3. Review portfolio ownership.
4. Give artisans a five-minute booking and payment walkthrough.
5. Reconcile provider payments and wallet entries daily.
6. Call customers after early completed jobs.
7. Record search terms with no supply.

Exit targets:

- Every funded payment reconciles.
- No unauthorized booking or chat access.
- Median first quote time is known.
- Completion and dispute rates are known.
- Support can explain each open case.

## Stage 4: paid public pilot

1. Publish approved privacy, terms, cancellation and refund rules.
2. Add public custom domain and restricted origins.
3. Switch Paystack to live after written approval.
4. Publish Android first if iOS review timing would delay controlled learning.
5. Open customer registration by supported location.
6. Add promo and referral rules only after payment reconciliation is stable.
7. Set handEwork Pro price only after the included benefits are operational.

Do not add more cities while the first city lacks enough available artisans for common searches.

## Stage 5: business and TVET

1. Select two or three businesses with recurring maintenance work.
2. Confirm requester, approver, spend-limit and invoice rules.
3. Sign a TVET institution agreement.
4. Verify the institution and each published course.
5. Add enrolment dates, fee, city, funding and issuing institution.
6. Measure whether training leads to profile verification and completed work.

## Manual implementation still required

These items cannot be completed by source code alone:

| Item | Owner action |
| --- | --- |
| Live mobile money | Business verification, contract, key and webhook approval |
| Escrow/hold model | Legal and provider approval of funds flow and language |
| Real artisan supply | Recruitment, ID review, trade proof, location and availability |
| WhatsApp | Business verification, number and approved templates |
| Push | EAS, FCM and APNs credentials |
| App stores | Developer accounts, policies, screenshots and review submission |
| MySQL safety | Paid persistent service, backups and tested restore |
| Object files | Bucket, access rules, scanning and retention |
| AI matching | Evaluated local-language dataset and approved model use |
| Multi-country | Company, tax, payment, consumer, privacy and support package per market |
| Legal documents | Final company details and Ghana-qualified approval |
| Disputes | Staff, evidence rules, authority and response times |

## Go/no-go rule

Do not accept public live payment if any of these is false:

- Signed webhook tested.
- Duplicate webhook tested.
- Refund tested.
- Held balance reconciled.
- Administrator available.
- KYC process active.
- Customer support route active.
- Privacy and terms approved.
- Backup restore tested.

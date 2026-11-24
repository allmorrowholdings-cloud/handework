# Marketplace release audit

## Release decision

Hold production sign-off for the full transaction journey. Guest requests, applicant onboarding and human review worked against the local Flask API. The outstanding commercial test is an assigned job taken from quotation through sandbox payment, customer acceptance, reconciliation and professional payout.

## What changed

The web application uses Next.js and React, with a second Vinext worker build. The Flask API uses SQLAlchemy, Alembic, JWT, Redis and Celery. MySQL, object storage and payment and messaging providers are deployment dependencies. The browser runs used a local production frontend build, disposable SQLite data and temporary file storage. No production records were created.

| Area | Changes |
| --- | --- |
| Homepage and discovery | Restored the signature headline and hammer artwork, removed the Figma player and moved the original Canva video below How it works. Playback is deferred and respects reduced motion. Service and problem searches accept location, support GPS, and distinguish unknown distance from a measured distance. Professional availability and shop listings use the API. |
| Booking and accounts | Visitors can write a request before signing in. Text and step survive same-tab refresh. Repeated web submissions carry a stable request key. Job records show status, evidence and a payment reference. The account shell resolves the role from the backend. Sign-in and sign-up wait for hydration and use POST. |
| Professional and administrator | Onboarding restores draft fields and asks again for the password. Verification reviewers can read private documents, record a decision and give an applicant a reason. Removing a mandatory approval updates marketplace eligibility. |
| Commerce and privacy | The API reuses pending charge references after uncertain submissions. Previously refunded records resist late success notifications. Local private files use expiring links. External provider access, retention and bucket policy still require deployment checks. The shop lists only supplier-confirmed product IDs. |
| Distribution | Updated public metadata routes, homepage styling and component copy. No schema migration in these commits. The Expo application was outside the browser test runs. |

Bizella gives customers recognisable reasons to book and describes who handles a problem. Taskrabbit makes choosing a professional a concrete next step. On handEwork, a customer can now see real supply or an explicit empty state. A remaining disadvantage is that an unassigned request has no automatic route to a professional. Social proof requires consented customer work and genuine feedback. [Bizella](https://bizella.com/) and [Taskrabbit](https://www.taskrabbit.com/).

## Journey evidence

| Status | Journey | Evidence and limit |
| --- | --- | --- |
| Pass | Guest through confirmed request record | Chrome followed signed-out My jobs to sign-in, drafted plumbing work, refreshed at place and time, created a customer account inline, submitted and read the resulting API-backed job. Confirmed here means a request was recorded. |
| Pass | Customer access and role routing | Visited dashboard, jobs, wallet, messages, notifications, settings, referrals and disputes. Customer access to the admin route redirected to the customer dashboard. Page visits cover rendering and navigation only. |
| Pass | New professional | Entered details, refreshed during setup, restored email and trade, re-entered password, registered and uploaded a test image as trade evidence. It remained pending review. |
| Pass | Administrator review | Signed in through the public form, opened an expiring private document, requested replacement with a reason and observed the same reason in the applicant account. No identity or trade qualification was approved in this run. |
| Pass | Public responsive layout | Visited 16 routes in both themes at 390 and 1440 px. Also tested home, marketplace, booking, onboarding and shop at 320, 375, 430, 768, 1024 and 1920 px. No horizontal overflow or HTTP error was observed in that sweep. The screenshot pairs cover five key pages. |
| Pass | Local account screens | Rendered eight professional routes and five admin routes and checked desktop and mobile widths. This includes the pending applicant's dashboard and the admin operations queue. |
| Fail | Unassigned request through quotation | The record is saved, but professionals see assigned bookings. Automatic dispatch is absent. The form explains the unassigned state and how to contact support. |
| Blocked | Approved professional through actual paid completion | Isolated integration tests exercise assigned bookings and quotations. No separately verified staging professional or test payment provider was available for an authenticated paid browser journey. |
| Blocked | Real Mobile Money confirmation, refunds and payout | Local tests cover failure, signed webhook handling and replay. Provider confirmation, settlement, reconciliation and bank or Mobile Money transfer need a configured sandbox and payout implementation. |
| Blocked | External delivery and shop fulfilment | Pending upload and review were verified locally. Live S3 ACLs, delivery through SMS, WhatsApp and Expo, supplier inventory and physical fulfilment require staging services and commercial records. |

### Performance and visual review

One fresh local production homepage load in Chrome at 390 by 844 measured LCP of 724 ms and CLS of 0. The frontend and API ran on the same machine. Field LCP, INP and 75th-percentile metrics remain unmeasured. Screenshot evidence is in [audit](audit/). Final visual review still calls for work on secondary surfaces in light mode, where some sections retain dark treatments. Screen-reader acceptance, real Android camera permissions and full WCAG conformance remain unverified.

### Operational limitations

Booking photos must be reselected after a refresh. Drafts are tab-local. The wider platform has no verified production test of all visible actions, shipping, protection policies or customer-approved public WorkProof stories. Paid ranking, guarantees and partner qualifications must be supported before publication. Spaces, Teams and diaspora-specific operations remain planned.

## Render, release and rollback

1. Use the backend API service's **Environment** panel and choose **Add variable**, then **Import from .env**. Use staging credentials first. Review the names before saving. Set the shared worker configuration on the Celery service as well. See the [official Render instructions](https://render.com/docs/configure-environment-variables).
2. Core backend names are `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `JWT_SECRET_KEY` and `WEB_ORIGINS`. Preserve the existing secret values when updating an established environment. Storage uses `S3_BUCKET`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `S3_PUBLIC_BASE_URL`. Confirm private objects cannot be retrieved through the public portfolio base URL.
3. Integration names are `PAYSTACK_SECRET_KEY`, `MAPBOX_SECRET_TOKEN`, `HUBTEL_CLIENT_ID`, `HUBTEL_CLIENT_SECRET`, `HUBTEL_SENDER_ID`, `WHATSAPP_PROVIDER_URL`, `WHATSAPP_PROVIDER_TOKEN` and `EXPO_ACCESS_TOKEN`. Set `SHOP_PUBLISHED_PRODUCT_IDS` to the comma-separated catalogue IDs whose specification, price and supply have been confirmed. Its empty default hides products from sale. Fees and release settings in the existing blueprint require operator review.
4. Configure `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_MAPBOX_TOKEN` on the frontend host. Build the frontend after changing public browser variables. Check health, allowed origins, an assigned booking, a private upload, a test-mode webhook and worker delivery in staging before releasing. See [deployment and integration details](DEPLOY_GITHUB_RENDER.md).
5. These changes require no new migration. Preserve the database and uploaded evidence. To roll back, deploy a previously tested compatible release. Older code cannot resolve new private-local references and restores weaker access controls. Keep private storage handling and payment retry protection in place during a selective rollback. Reconcile pending references with the payment provider before retrying charges.

## Validation commands

- `npm run build:vercel` passed, including TypeScript and generation of 39 static pages.
- `npm test` passed the Vinext build and two rendered HTML regressions. They verify the public homepage and safe server-rendered authentication forms.
- `npm run lint` returned zero errors and nine warnings about existing image elements.
- `python -m pytest backend/tests --disable-warnings --no-cov -o addopts=` passed all 33 tests. New cases cover a lost booking response, a payment-provider timeout, plain-language location matching catalogue publication, the professional's incoming request notification, the customer's quote reference and eligibility at quote acceptance.
- The role walkthrough used a disposable SQLite file, separate customer, applicant and administrator browser contexts and the real HTTP API. Provider money movement and a genuine verification approval were excluded. A local administrator requested replacement of an intentionally unsuitable test image.

Assigned quote requests now create an in-app notification for the selected professional. Submitted quote notices include the real quote ID and currency. Acceptance rechecks professional eligibility, and ordinary status updates cannot directly mark a job paid or refunded. These last changes were verified in the Flask test suite. External notification delivery remains blocked.

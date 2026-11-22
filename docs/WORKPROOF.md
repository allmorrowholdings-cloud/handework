# handEwork WorkProof™

WorkProof is handEwork's portable work-reputation layer for skilled workers. It prioritises verified economic activity and actual work history, not certificates alone.

- Completed platform bookings become eligible evidence.
- Outside jobs remain pending until an independent client or business is checked.
- Public records never expose verifier contact details or earnings without consent.
- Rejected, revoked or pending evidence does not increase the score.
- Workers see submission status and decision reasons; admin decisions are audited.

The 0–1,000 indicator uses verified jobs, completion, ratings, repeat clients, years of verified activity, identity verification and unresolved disputes. It is a work-reputation indicator—not a credit score, lending decision, employment guarantee or substitute for due diligence.

Endpoints: `GET /v1/workproof/<artisan_id>`, `GET|POST /v1/workproof/me`, and `POST /v1/admin/workproof/<evidence_id>/decision`.

Partner APIs, consented earnings bands, references, qualifications, training and microcredentials can extend the evidence model without changing its public privacy boundary.

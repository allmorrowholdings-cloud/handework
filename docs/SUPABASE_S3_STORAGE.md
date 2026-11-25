# handEwork file storage

The API writes files through boto3 to Supabase Storage's S3-compatible API. Objects are private and remain inaccessible without a short-lived signed URL. The app database remains TiDB; it stores object key, bucket, MIME type, byte size, SHA-256 digest, original filename, owner, business purpose, related booking, and replacement/deletion timestamps.

## Render environment

Set these values on both the `handework-api` web service and `handework-worker` where applicable:

| Variable | Value |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | Supabase Storage S3 access key |
| `AWS_SECRET_ACCESS_KEY` | Corresponding secret; keep in Render secret environment |
| `AWS_REGION` | Region shown for the Supabase project |
| `S3_ENDPOINT_URL` | `https://<project-ref>.supabase.co/storage/v1/s3` |
| `STORAGE_MODE` | `s3` |
| `S3_PRIVATE_BUCKET` | `handework-private` |
| `S3_MEDIA_BUCKET` | `handework-media` |
| `S3_EVIDENCE_BUCKET` | `handework-evidence` |

Create the three buckets in Supabase Storage and leave each private. Keep the generated S3 credentials on the server. They grant access across the project's buckets and bypass Storage RLS. No Supabase service-role key is used by the application. Do not configure public bucket URLs or put storage keys in `NEXT_PUBLIC_*` variables.

Identity verification documents use `handework-private`; completion, dispute, and WorkProof evidence use `handework-evidence`; portfolio, avatars, booking attachments, chat media and shop images use `handework-media`. All three buckets are private. The app issues signed URLs with a maximum lifetime of 15 minutes (normally 5 minutes).

The API validates extension-appropriate MIME signatures and rejects empty or oversized files (15 MiB maximum). `FileAsset` records ownership and metadata in TiDB. User downloads require an authenticated ownership/booking-participant check; administrator review routes retain their server-side admin role checks. Replacements create a new asset record and mark the old record deleted. Deletions are audited and soft-delete metadata before removing the object. If provider deletion fails, the API records the exception for operational cleanup rather than claiming object deletion succeeded.

## Database migration

The additive Alembic revision `a8e4c17b6321` follows the existing payment revision `ab340c901fe2`, itself based on production head `f38f11b71ae0`. Deploy the API image, then run the existing Render migration command (`flask --app handework db upgrade`) against the configured TiDB `DATABASE_URL`. This applies the existing payment migration and then the storage migration. Do not use `db.create_all` against production. Verify `alembic_version` is `a8e4c17b6321` and the new nullable asset associations and `shop_product_media` table are present before enabling uploads.

No migration copies legacy objects. Existing `s3://` references are signed using the configured endpoint. Before switching providers, verify that any legacy bucket and key exist at that endpoint. Files recorded in local development storage are not migrated; they must be re-uploaded from the original source before production use.

## Operational checks

Before production cutover, upload one non-sensitive image and PDF from an artisan account, confirm the bucket/key and metadata in TiDB, fetch the download URL as its owner, confirm an unrelated account receives 404, verify expiry, replace the file, and verify the old object is removed. Repeat for identity and booking evidence with administrator review. Do not upload live identity documents as a smoke test unless the test account and retention policy are approved.

The platform does not currently perform malware scanning. New `FileAsset.scan_status` remains `pending`; configure a scanning service and a review process before treating files as malware-cleared. Supabase Storage's at-rest security depends on the configured Supabase project and its account controls.

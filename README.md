# handEwork

handEwork connects people in Ghana with artisans for repairs, installations and custom work. Customers can search by trade and area, request a quote, agree on materials and labour, and review the finished job. Each booking keeps the conversation, photos and approvals together.

Artisans use handEwork to show past work, publish availability, send quotes and manage jobs. The operations team reviews verification requests, payments and disputes.

## Stack

The web app uses Next.js, React and TypeScript. The mobile app uses React Native and Expo. A Python Flask API handles bookings and payments, with SQLAlchemy and MySQL for records, Redis and Celery for background jobs, and Socket.IO for messaging. Mapbox provides maps and Paystack handles payment processing.

### Transactional email

Set `EMAIL_PROVIDER=gmail_apps_script` on the API and Celery worker. Configure the deployed HTTPS `EMAIL_SERVICE_URL` and its matching `EMAIL_SERVICE_SECRET` as server-side secrets. Both services must share the application `SECRET_KEY`, database and broker. Migration `ca72e0fa93bd` initializes the recipient budget. Run the worker with Celery Beat as shown in `render.yaml` so committed notifications survive broker interruptions.

The worker signs the UTF-8 payload with the Unix timestamp in milliseconds and a fresh nonce. It accepts an explicit JSON success acknowledgement and follows the Apps Script Content Service redirect with a GET. The default `EMAIL_DAILY_RECIPIENT_LIMIT` is 100 for the sending account. Set it to the budget available to this application. A provider quota rejection pauses sends for 24 hours. [Google Apps Script quotas](https://developers.google.com/apps-script/guides/services/quotas)

Email notification rows record the delivery outcome. Safe connection failures retry up to five total attempts. An ambiguous response or interrupted send is recorded as `unknown`; check the sender's records before resending. For `authentication` or `configuration` outcomes, check the endpoint and credentials. Account holders can request fresh, single-use verification and recovery codes from the sign-in page. Codes expire after 20 minutes.

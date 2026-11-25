import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

from flask import current_app

from ..extensions import db
from ..models import EmailQuota, Notification, User
from .gmail import send_email

DAY = timedelta(days=1)
CODE_LIFETIME = timedelta(minutes=20)
ACCOUNT_SUBJECTS = {"verify": "Welcome to handEwork - verify your email", "reset": "Reset your handEwork password"}


def enabled():
    return os.getenv("EMAIL_PROVIDER") == "gmail_apps_script"


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def queue_email(user, title, body, data=None):
    if enabled() and ((data or {}).get('account_action') or (user.notification_preferences or {}).get('email', True)):
        row = Notification(user_id=user.id, channel="email", title=title[:180], body=body[:700], data=data or {})
        db.session.add(row)
        return row


def booking_email(booking, subject, text, exclude=None):
    recipients = [booking.customer]
    if booking.artisan:
        recipients.append(booking.artisan.user)
    for user in recipients:
        if user.id != exclude:
            queue_email(user, subject, text, {"booking_id": booking.id})


def queue_account_email(user, action):
    # Invalidate all previously issued codes of this kind, including delayed deliveries.
    Notification.query.filter_by(user_id=user.id, channel="email", title=ACCOUNT_SUBJECTS[action],
                                 read_at=None).update({"read_at": datetime.now(timezone.utc)})
    return queue_email(user, ACCOUNT_SUBJECTS[action],
                       "Enter this code on the handEwork account page. It expires in 20 minutes.",
                       {"account_action": action})


def account_code(row, user):
    material = f"email-code:{row.id}:{user.id}:{user.email}:{row.title}:{user.session_version}"
    return hmac.new(current_app.config["SECRET_KEY"].encode(), material.encode(), hashlib.sha256).hexdigest()[:16]


def due(now):
    return db.or_(Notification.next_attempt.is_(None), Notification.next_attempt <= now)


def deliver_email(notification_id):
    now = datetime.now(timezone.utc)
    row = Notification.query.filter_by(id=notification_id, channel="email", status="queued").filter(
        due(now)).with_for_update().first()
    if not row:
        return
    user = db.session.get(User, row.user_id)
    text = row.body
    if (row.data or {}).get("account_action"):
        if row.read_at or utc(row.created_at) + CODE_LIFETIME <= now:
            row.status = "expired"
            db.session.commit()
            return
        text += " Code: " + account_code(row, user)
        action = row.data["account_action"]
        page = "Forgot password?" if action == "reset" else "Verify email"
        text += f" Open the handEwork sign-in page and select {page}."
    quota = EmailQuota.query.filter_by(id=1).with_for_update().one()
    if not quota.window_start or utc(quota.window_start) + DAY <= now:
        quota.window_start, quota.reserved = now, 0
    limit = int(os.getenv("EMAIL_DAILY_RECIPIENT_LIMIT", "100"))
    resume = utc(quota.blocked_until)
    if quota.reserved >= limit:
        resume = max(resume or now, utc(quota.window_start) + DAY)
    if resume and resume > now:
        row.next_attempt = resume
        db.session.commit()
        return
    quota.reserved += 1
    row.attempts += 1
    # Commit the claim before HTTP. A crash after POST must never trigger a blind resend.
    row.status, row.next_attempt = "sending", now + timedelta(minutes=5)
    address, title = user.email, row.title
    db.session.commit()
    result = send_email(address, title, text)
    row.status, row.next_attempt = result, None
    if result == "sent":
        row.sent_at = datetime.now(timezone.utc)
    elif result in {"retry", "quota"}:
        quota = EmailQuota.query.filter_by(id=1).with_for_update().one()
        if utc(quota.window_start) <= now:
            quota.reserved = max(0, quota.reserved - 1)
        if result == "quota":
            quota.blocked_until = datetime.now(timezone.utc) + DAY
        if row.attempts < 5:
            row.status = "queued"
            row.next_attempt = quota.blocked_until if result == "quota" else now + timedelta(seconds=30 * 2**(row.attempts-1))
        else:
            row.status = "failed"
    db.session.commit()
    current_app.logger.info("Email notification %s outcome=%s", notification_id, result)

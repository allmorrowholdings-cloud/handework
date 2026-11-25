import os
from datetime import datetime, timedelta, timezone
from celery import Celery
from .services.email_delivery import deliver_email, due
from . import create_app
from .extensions import db
from .models import Notification, PushDevice, User
from .services.notifications import send_expo, send_sms, send_whatsapp

celery = Celery("handework", broker=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"), backend=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
celery.conf.update(task_acks_late=True, task_reject_on_worker_lost=True, broker_transport_options={"visibility_timeout": 3600})
celery.conf.beat_schedule = {"email-outbox": {"task": "handework.tasks.drain_email", "schedule": 30.0}}
flask_app = create_app(seed_development_admin=False)


class FlaskTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with flask_app.app_context(): return self.run(*args, **kwargs)

celery.Task = FlaskTask


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def deliver_notification(self, notification_id):
    row=db.session.get(Notification,notification_id)
    if not row or row.status=="sent":return
    if row.channel == "email":
        return deliver_email(row.id)
    user=db.session.get(User,row.user_id)
    if row.channel=="push":
        return deliver_push_safely(row.id)
    elif row.channel == "sms":
        return deliver_sms_safely(row.id)
    elif row.channel=="whatsapp":send_whatsapp(user.phone,row.body)
    row.status="sent";row.sent_at=db.func.now();db.session.commit()



def deliver_sms_safely(notification_id):
    from .services.arkesel import sms_enabled, normalize_phone

    if not sms_enabled():
        return

    row = db.session.get(Notification, notification_id)

    if not row or row.channel != "sms" or row.status != "queued":
        return

    user = db.session.get(User, row.user_id)

    try:
        phone = normalize_phone(user.phone if user else None)
    except ValueError:
        row.status = "failed"
        db.session.commit()
        return

    message = row.body

    claimed = Notification.query.filter_by(
        id=notification_id,
        channel="sms",
        status="queued"
    ).update(
        {
            "status": "sending",
            "next_attempt": datetime.now(timezone.utc) + timedelta(minutes=10),
            "attempts": Notification.attempts + 1
        },
        synchronize_session=False
    )

    db.session.commit()

    if claimed != 1:
        return

    try:
        send_sms("+" + phone, message)
    except Exception:
        Notification.query.filter_by(
            id=notification_id,
            status="sending"
        ).update(
            {"status": "unknown"},
            synchronize_session=False
        )
        db.session.commit()
        return

    Notification.query.filter_by(
        id=notification_id,
        status="sending"
    ).update(
        {
            "status": "sent",
            "sent_at": db.func.now()
        },
        synchronize_session=False
    )
    db.session.commit()


@celery.task
def drain_email():
    from .services.email_delivery import enabled
    if not enabled():
        return
    now = datetime.now(timezone.utc)
    Notification.query.filter_by(channel="email", status="sending").filter(due(now)).update(
        {"status": "unknown", "next_attempt": None}, synchronize_session=False)
    db.session.commit()
    ids = db.session.query(Notification.id).filter_by(channel="email", status="queued").filter(
        due(now)).order_by(Notification.created_at).limit(100).all()
    for (notification_id,) in ids:
        deliver_notification.delay(notification_id)



def deliver_push_safely(notification_id):
    from .services.firebase_push import (
        enabled as firebase_enabled,
        send_web_push
    )

    row = db.session.get(Notification, notification_id)

    if not row or row.channel != "push" or row.status != "queued":
        return

    user = db.session.get(User, row.user_id)

    if not user or user.status != "active" or not (
        user.notification_preferences or {}
    ).get("push", True):
        row.status = "skipped"
        db.session.commit()
        return

    claimed = Notification.query.filter_by(
        id=notification_id,
        channel="push",
        status="queued"
    ).update(
        {
            "status": "sending",
            "next_attempt": datetime.now(timezone.utc) + timedelta(minutes=10),
            "attempts": Notification.attempts + 1
        },
        synchronize_session=False
    )

    db.session.commit()

    if claimed != 1:
        return

    devices = PushDevice.query.filter_by(
        user_id=user.id,
        active=True
    ).all()

    accepted = 0
    failed = 0

    for device in devices:
        try:
            if device.platform == "web":
                if not firebase_enabled():
                    continue

                result = send_web_push(device.expo_push_token)

                if result == "expired":
                    device.active = False
                elif result == "accepted":
                    accepted += 1

            elif (
                os.getenv("EXPO_PUSH_ENABLED", "false").lower() == "true"
                and device.expo_push_token.startswith(
                    ("ExpoPushToken", "ExponentPushToken")
                )
            ):
                result = send_expo(
                    [device.expo_push_token],
                    "handEwork",
                    "You have a new account update.",
                    {}
                )

                tickets = result.get("data", [])

                if isinstance(tickets, dict):
                    tickets = [tickets]

                for ticket in tickets:
                    if ticket.get("status") == "ok":
                        accepted += 1
                    elif ticket.get("details", {}).get(
                        "error"
                    ) == "DeviceNotRegistered":
                        device.active = False
                    else:
                        failed += 1

                if not tickets:
                    failed += 1

        except Exception:
            failed += 1

    row.status = (
        "unknown" if failed
        else "sent" if accepted
        else "skipped"
    )

    if accepted:
        row.sent_at = db.func.now()

    db.session.commit()

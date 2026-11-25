import hmac
import os
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Notification
from ..services.email_delivery import deliver_email, due
from ..services.firebase_push import enabled as firebase_enabled
from ..services.arkesel import sms_enabled

bp = Blueprint("scheduler", __name__)


def authorized():
    secret = os.getenv("NOTIFICATION_SCHEDULER_TOKEN", "")

    return len(secret) >= 32 and hmac.compare_digest(
        request.headers.get("Authorization", ""),
        "Bearer " + secret
    )


@bp.post("/internal/notifications/tick")
def notification_tick():
    if not authorized():
        return jsonify(message="Forbidden"), 403

    if os.getenv("NOTIFICATION_SCHEDULER_ENABLED", "false").lower() != "true":
        return jsonify(processed=0, enabled=False)

    from ..services.email_delivery import enabled as email_enabled
    from ..tasks import deliver_sms_safely, deliver_push_safely

    channels = []

    if email_enabled():
        channels.append("email")

    if sms_enabled():
        channels.append("sms")

    if firebase_enabled() or os.getenv(
        "EXPO_PUSH_ENABLED", "false"
    ).lower() == "true":
        channels.append("push")

    if not channels:
        return jsonify(processed=0, enabled=True)

    now = datetime.now(timezone.utc)

    Notification.query.filter(
        Notification.channel.in_(["sms", "push"]),
        Notification.status == "sending",
        Notification.next_attempt.is_not(None),
        Notification.next_attempt <= now
    ).update(
        {
            "status": "unknown",
            "next_attempt": None
        },
        synchronize_session=False
    )

    db.session.commit()

    ids = db.session.query(Notification.id, Notification.channel).filter(
        Notification.status == "queued",
        Notification.channel.in_(channels)
    ).filter(
        due(now)
    ).order_by(
        Notification.created_at
    ).limit(1).all()

    db.session.remove()

    processed = 0
    errors = 0

    for notification_id, channel in ids:
        try:
            if channel == "email":
                deliver_email(notification_id)
            elif channel == "sms":
                deliver_sms_safely(notification_id)
            elif channel == "push":
                deliver_push_safely(notification_id)

            processed += 1

        except Exception:
            db.session.rollback()
            errors += 1

        finally:
            db.session.remove()

    return jsonify(
        processed=processed,
        errors=errors,
        enabled=True
    )

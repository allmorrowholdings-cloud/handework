import os
from datetime import datetime, timezone
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
        tokens=[x.expo_push_token for x in PushDevice.query.filter_by(user_id=user.id,active=True).all()];send_expo(tokens,row.title,row.body,row.data)
    elif row.channel=="sms":send_sms(user.phone,row.body)
    elif row.channel=="whatsapp":send_whatsapp(user.phone,row.body)
    row.status="sent";row.sent_at=db.func.now();db.session.commit()


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

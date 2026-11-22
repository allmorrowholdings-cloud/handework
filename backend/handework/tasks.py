import os
from celery import Celery
from . import create_app
from .extensions import db
from .models import Notification, PushDevice, User
from .services.notifications import send_expo, send_sms, send_whatsapp

celery = Celery("handework", broker=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"), backend=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
celery.conf.update(task_acks_late=True, task_reject_on_worker_lost=True, broker_transport_options={"visibility_timeout": 3600})
flask_app = create_app()


class FlaskTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with flask_app.app_context(): return self.run(*args, **kwargs)

celery.Task = FlaskTask


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def deliver_notification(self, notification_id):
    row=db.session.get(Notification,notification_id)
    if not row or row.status=="sent":return
    user=db.session.get(User,row.user_id)
    if row.channel=="push":
        tokens=[x.expo_push_token for x in PushDevice.query.filter_by(user_id=user.id,active=True).all()];send_expo(tokens,row.title,row.body,row.data)
    elif row.channel=="sms":send_sms(user.phone,row.body)
    elif row.channel=="whatsapp":send_whatsapp(user.phone,row.body)
    row.status="sent";row.sent_at=db.func.now();db.session.commit()

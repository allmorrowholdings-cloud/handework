from datetime import datetime, timedelta, timezone
from ..models import PaymentJob
from ..extensions import db


def enqueue(kind, record_id, hours=0):
    key = kind + ":" + record_id
    if not db.session.get(PaymentJob, key):
        db.session.add(PaymentJob(key=key, kind=kind, record_id=record_id,
                                  due_at=datetime.now(timezone.utc) + timedelta(hours=hours)))

import hmac
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from flask import abort, jsonify, request
from werkzeug.exceptions import HTTPException
from ..extensions import db
from ..models import (ArtisanProfile, Booking, BookingStatus, BookingStatusEvent, FileAsset, Notification,
                      Payment, PaymentJob, PaymentOperation, PaymentStatus, PayoutRecipient, RiskEvent)
from ..services.paystack import enabled, matches, minor
from .payments import bp, complete_release, control_for, verify_charge
from .payment_ops import lock_payment, net, reconcile, remote, record_settlement, start_operation
from ..services.notifications import dispatch_notifications


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def auto_release(booking_id):
    booking = Booking.query.filter_by(id=booking_id).with_for_update().one()
    if booking.status == BookingStatus.COMPLETED:
        return True
    if not enabled("PAYMENT_AUTO_RELEASE_ENABLED") or booking.status != BookingStatus.COMPLETION_SUBMITTED:
        return False
    event = BookingStatusEvent.query.filter_by(booking_id=booking.id, to_status="completion_submitted").order_by(BookingStatusEvent.occurred_at.desc()).first()
    if not event or not booking.artisan or booking.artisan.verification_status != "approved":
        return False
    evidence = FileAsset.query.filter_by(booking_id=booking.id, owner_id=booking.artisan.user_id, purpose="completion_evidence").first()
    recipient = db.session.get(PayoutRecipient, booking.artisan_id)
    if not evidence or not recipient:
        return False
    notices = Notification.query.filter(Notification.user_id == booking.customer_id, Notification.channel=="in_app",
                                        Notification.created_at >= event.occurred_at).all()
    notice = next((n for n in notices if (n.data or {}).get("booking_id") == booking.id and n.title == "Booking updated"
                   and "completion submitted" in n.body), None)
    if not notice:
        return False
    payments = Payment.query.filter_by(booking_id=booking.id, status=PaymentStatus.HELD).order_by(Payment.id).with_for_update().all()
    if not payments:
        return False
    required = Decimal("0")
    for payment in payments:
        control = control_for(payment)
        if not control.auto_hours or control.provider_hold or not control.settlement_id:
            return False
        if max(utc(event.occurred_at), utc(notice.created_at), utc(evidence.created_at)) + timedelta(hours=control.auto_hours) > datetime.now(timezone.utc):
            return False
        if RiskEvent.query.filter_by(payment_id=payment.id).filter(RiskEvent.decision.in_(["review","block"])).first():
            return False
        required += net(payment, payment.amount-control.refunded)
    balances = remote("GET","/balance")
    if not any(b.get("currency")==booking.currency and b.get("balance",0)>=minor(required) for b in balances):
        return False
    result = complete_release(booking, None)
    if isinstance(result, tuple):
        abort(409, description="Release requires review")
    return True


def find_settlement(job, payment):
    control = control_for(payment)
    if control.settlement_id:
        return True
    # Walk one provider page per tick so large merchant accounts make progress.
    cursor = job.cursor or {}
    batch_page = cursor.get("batch_page", 1)
    batch_index = cursor.get("batch_index", 0)
    tx_page = cursor.get("tx_page", 1)
    batches = remote("GET", "/settlement", params={"status":"success", "from":payment.created_at.date().isoformat(),
                                                  "page":batch_page, "perPage":50})
    if batch_index >= len(batches):
        job.cursor = {"batch_page": batch_page+1} if len(batches)==50 else {}
        return False
    batch = batches[batch_index]
    rows = remote("GET", f"/settlement/{int(batch['id'])}/transactions", params={"page":tx_page, "perPage":100})
    for row in rows:
        if batch.get("status")=="success" and matches(row, payment.provider_reference, payment.amount, payment.currency):
            record_settlement(payment, str(batch["id"]), rows, None)
            return True
    job.cursor = {"batch_page":batch_page, "batch_index":batch_index if len(rows)==100 else batch_index+1,
                  "tx_page":tx_page+1 if len(rows)==100 else 1}
    return False


def run_job(job):
    if job.kind == "auto_release":
        return auto_release(job.record_id)
    if job.kind == "verify_operation":
        op = db.session.get(PaymentOperation, job.record_id)
        reconciled = reconcile(op)
        if reconciled.kind == "payout" and reconciled.status == "failed" and enabled("PAYMENT_AUTO_PAYOUT_ENABLED"):
            from ..services.payment_jobs import enqueue
            attempts = PaymentOperation.query.filter_by(kind="payout", payment_id=op.payment_id).count()
            if attempts < int(os.getenv("PAYMENT_TRANSFER_MAX_ATTEMPTS","3")):
                enqueue("retry_payout", op.id, hours=1)
        return reconciled.status != "pending"
    if job.kind == "retry_payout":
        previous = db.session.get(PaymentOperation, job.record_id)
        if previous.status != "failed":
            return True
        if not all(enabled(flag) for flag in ("PAYMENTS_ENABLED","PAYSTACK_TRANSFERS_ENABLED","PAYMENT_AUTO_PAYOUT_ENABLED")):
            return False
        latest = PaymentOperation.query.filter_by(payment_id=previous.payment_id, kind="payout").order_by(PaymentOperation.created_at.desc()).first()
        if latest.id == previous.id:
            start_operation(previous.payment_id, "payout", "retry-"+previous.id, {}, None)
        return True
    payment = lock_payment(job.record_id)
    if job.kind == "verify_charge":
        if payment.status == PaymentStatus.PENDING:
            ids = verify_charge(payment)
            db.session.commit()
            dispatch_notifications(ids)
        return payment.status != PaymentStatus.PENDING
    if job.kind == "settlement":
        return find_settlement(job, payment)
    if job.kind == "auto_payout":
        if not all(enabled(flag) for flag in ("PAYMENTS_ENABLED","PAYSTACK_TRANSFERS_ENABLED","PAYMENT_AUTO_PAYOUT_ENABLED")):
            return False
        ops = PaymentOperation.query.filter_by(payment_id=payment.id, kind="payout").all()
        if any(op.status in {"pending","success"} for op in ops):
            return True
        start_operation(payment.id, "payout", "auto-"+payment.id+"-"+str(len(ops)), {}, None)
        return True
    raise ValueError("Unknown job")


@bp.post("/internal/payments/tick")
def tick():
    secret = os.getenv("PAYMENT_SCHEDULER_TOKEN","")
    if len(secret)<32 or not hmac.compare_digest(request.headers.get("Authorization",""), "Bearer "+secret):
        abort(403)
    now = datetime.now(timezone.utc)
    job = PaymentJob.query.filter(PaymentJob.state=="pending", PaymentJob.due_at<=now).order_by(PaymentJob.due_at).with_for_update().first()
    if not job:
        return jsonify(processed=0)
    # Durable lease survives process death. All effects have independent DB claims.
    job.due_at = now + timedelta(minutes=5)
    job.attempts += 1
    key = job.key
    db.session.commit()
    try:
        done = run_job(job)
        job.state = "done" if done else "pending"
        job.last_error = None
    except Exception as exc:
        db.session.rollback()
        job = db.session.get(PaymentJob, key)
        job.last_error = str(exc.code) if isinstance(exc, HTTPException) else type(exc).__name__
    if job.state != "done":
        job.due_at = datetime.now(timezone.utc) + timedelta(minutes=min(60, 2**min(job.attempts,6)))
    db.session.commit()
    return jsonify(processed=1, state=job.state, error=job.last_error)

import os
import secrets
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from flask import abort, Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from ..services.email_delivery import queue_email
from ..extensions import db, limiter
from ..models import ArtisanProfile, Booking, BookingStatus, BookingStatusEvent, LedgerEntry, Payment, PaymentStatus, RiskEvent, Role, ShopOrder, WalletAccount
from ..security import current_user, role_required
from ..services.paystack import Paystack, checkout_enabled, checkout_url, enabled, matches, NETWORKS
from ..models import PaymentControl, PaymentOperation, PaymentReceipt, Dispute, AuditLog
from ..services.payment_jobs import enqueue
from ..services.payment_plan import installments
from ..services.commission import commission, commission_bps
from ..services.journal import post
from ..services.risk import payment_risk
from ..services.notifications import dispatch_notifications, queue_notifications

bp = Blueprint("payments", __name__)

from werkzeug.exceptions import HTTPException


@bp.errorhandler(HTTPException)
def payment_error(error):
    db.session.rollback()
    return jsonify(message=error.description), error.code


def wallet_for(user_id, currency="GHS"):
    wallet = WalletAccount.query.filter_by(user_id=user_id, currency=currency).with_for_update().first()
    if not wallet:
        wallet = WalletAccount(user_id=user_id, currency=currency); db.session.add(wallet); db.session.flush()
    return wallet


def mark_funded(payment, payload):
    if payment.status in (PaymentStatus.HELD, PaymentStatus.RELEASED, PaymentStatus.REFUNDED, PaymentStatus.REFUND_PENDING): return []
    booking = Booking.query.filter_by(id=payment.booking_id).with_for_update().one()
    payment.status, payment.paid_at, payment.provider_payload = PaymentStatus.HELD, datetime.now(timezone.utc), payload
    customer_wallet = wallet_for(payment.customer_id, payment.currency)
    customer_wallet.held_balance += payment.amount
    post(payment.id, "collection", "provider_receivable", "booking_liability", payment.amount, payment.currency)
    db.session.add(LedgerEntry(account_id=customer_wallet.id, payment_id=payment.id, booking_id=booking.id, direction="credit", bucket="held", amount=payment.amount, currency=payment.currency, event_type="payment_funded", external_reference=payment.provider_reference))
    enqueue("settlement", payment.id)
    if booking.status == BookingStatus.ACCEPTED:
        before = booking.status.value; booking.status = BookingStatus.FUNDED
        db.session.add(BookingStatusEvent(booking_id=booking.id, actor_id=booking.customer_id, from_status=before, to_status=booking.status.value, note="Payment confirmed and held"))
    recipients=[booking.customer]
    if booking.artisan: recipients.append(booking.artisan.user)
    ids=[]
    for recipient in recipients: ids.extend(queue_notifications(recipient,"Payment confirmed",f"{payment.currency} {float(payment.amount):.2f} is held for {booking.reference}.",{"booking_id":booking.id,"payment_id":payment.id},urgent=True))
    return ids


@bp.post("/payments/checkout")
@bp.post("/payments/mobile-money")
@role_required(Role.CUSTOMER)
@limiter.limit("5 per minute")
def mobile_money():
    user = current_user(); data = request.get_json(silent=True) or {}; booking = Booking.query.filter_by(id=data.get("booking_id"), customer_id=user.id).with_for_update().first_or_404()
    if not checkout_enabled(user, booking): return jsonify(message="Payments are disabled"), 503
    if booking.currency != "GHS" or not booking.agreed_amount or booking.agreed_amount <= 0: return jsonify(message="Invalid booking amount"), 409
    if booking.status not in {BookingStatus.ACCEPTED, BookingStatus.FUNDED, BookingStatus.EN_ROUTE, BookingStatus.IN_PROGRESS, BookingStatus.COMPLETION_SUBMITTED}: return jsonify({"message": "Accept an artisan quote before payment", "code": "booking_not_payable"}), 409
    idem = request.headers.get("Idempotency-Key") or data.get("idempotency_key")
    if not isinstance(idem, str) or not 1 <= len(idem) <= 100: return jsonify({"message": "Idempotency-Key is required", "code": "missing_idempotency_key"}), 400
    existing = Payment.query.filter_by(idempotency_key=idem).first()
    if existing:
        if existing.customer_id != user.id or existing.booking_id != booking.id: return jsonify({"message": "Idempotency key is already in use", "code": "idempotency_conflict"}), 409
        return jsonify({"payment_id": existing.id, "reference": existing.provider_reference, "status": existing.status.value, "authorization_url": (existing.provider_payload or {}).get("authorization_url")})
    pending = Payment.query.filter_by(booking_id=booking.id, status=PaymentStatus.PENDING).with_for_update().first()
    if pending:
        return jsonify({"payment_id":pending.id, "reference":pending.provider_reference, "status":"pending", "authorization_url":(pending.provider_payload or {}).get("authorization_url")}), 202
    stages = installments(booking)
    stage = next((s for s in stages if s["status"] == "unpaid"), None)
    if not stage or data.get("claim", stage["claim"]) != stage["claim"]:
        return jsonify(message="Refresh the payment schedule before checkout"), 409
    amount = Decimal(stage["amount"])
    phone, network = str(data.get("phone") or user.phone), str(data.get("network") or "")
    hosted = request.path.endswith("/checkout")
    if not hosted and network.lower().replace(" ", "") not in NETWORKS:
        return jsonify(message="Unsupported mobile-money network"), 422
    score, signals = payment_risk(user, amount, phone, network)
    reference = f"handEwork-{secrets.token_hex(8).upper()}"
    fee = commission(amount, commission_bps(booking.service))
    payment = Payment(booking_id=booking.id, customer_id=user.id, artisan_id=booking.artisan_id, provider_reference=reference, idempotency_key=idem, channel="checkout" if hosted else "mobile_money", network=network, amount=amount, platform_fee=fee, currency=booking.currency)
    db.session.add(payment)
    try:
        db.session.flush()
        terms = os.getenv("PAYMENT_AUTO_RELEASE_TERMS_VERSION", "")
        agreed = enabled("PAYMENT_AUTO_RELEASE_ENABLED") and terms and data.get("terms_version") == terms
        hours = int(os.getenv("PAYMENT_AUTO_RELEASE_HOURS", "48")) if agreed else None
        if hours is not None and hours <= 0:
            abort(503, description="Invalid release interval")
        db.session.add(PaymentControl(payment_id=payment.id, booking_claim=stage["claim"],
                                      terms_version=terms if agreed else None, auto_hours=hours))
        enqueue("verify_charge", payment.id)
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return jsonify(message="This payment already has an active request"), 409
    db.session.add(RiskEvent(user_id=user.id, booking_id=booking.id, payment_id=payment.id, kind="payment_initiation", score=score, signals=signals, decision="block" if score >= 90 else "review" if score >= 60 else "allow"))
    if score >= 90: db.session.get(PaymentControl, payment.id).booking_claim = None; payment.status = PaymentStatus.FAILED; db.session.commit(); return jsonify({"message": "Payment requires manual review", "code": "risk_hold"}), 409
    if not os.getenv("PAYSTACK_SECRET_KEY"):
        db.session.rollback()
        return jsonify({"message": "Mobile money is unavailable right now."}), 503
    db.session.commit()
    try:
        if hosted:
            provider = Paystack().initialize_transaction(email=user.email, amount_ghs=payment.amount, reference=reference,
                callback_url=os.getenv("PUBLIC_WEB_URL", "http://localhost:3000").rstrip("/") + "/bookings/" + booking.id)
        else:
            provider = Paystack().mobile_money_charge(email=user.email, amount_ghs=amount, phone=phone, network=network, reference=reference)
    except Exception: db.session.rollback(); return jsonify({"message": "Payment confirmation is unavailable. Check the booking before trying again.", "code": "provider_unavailable"}), 502
    result = provider.get("data") or {}
    if result.get("reference") != reference or (hosted and not checkout_url(result)):
        return jsonify(message="Provider reference requires reconciliation"), 502
    payment.provider_payload = {"authorization_url": checkout_url(result)} if hosted else {"status": result.get("status")}
    db.session.commit()
    return jsonify({"payment_id": payment.id, "reference": reference, "status": payment.status.value, "authorization_url": checkout_url(result), "provider": {"status": result.get("status")}}), 202


@bp.post("/webhooks/paystack")
@limiter.exempt
def paystack_webhook():
    raw = request.get_data(); signature = request.headers.get("x-paystack-signature", "")
    try: valid = Paystack().verify_signature(raw, signature)
    except Exception: return jsonify({"message": "Payment webhook is not configured"}), 503
    if not valid: return jsonify({"message": "Invalid signature"}), 401
    payload = request.get_json(silent=True) or {}
    data = payload.get("data") or {}
    event = payload.get("event", "")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        db.session.add(PaymentReceipt(digest=digest, event=str(event)[:64], reference=str(data.get("reference") or data.get("id") or "")[:120]))
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return jsonify(received=True)
    if event.startswith(("refund.", "transfer.")):
        from .payment_ops import reconcile_event
        reconcile_event(event, data)
    elif event.startswith("charge.dispute."):
        from .payment_ops import sync_dispute
        transaction = data.get("transaction") or {}
        ref = transaction.get("reference") if isinstance(transaction, dict) else None
        if ref and (Payment.query.filter_by(provider_reference=ref).first() or ShopOrder.query.filter_by(provider_reference=ref).first()):
            sync_dispute(str(data.get("id","")), ref)
    elif event in {"charge.success", "charge.successful", "charge.failed", "charge.abandoned"}:
        ref = data.get("reference")
        payment = Payment.query.filter_by(provider_reference=ref).with_for_update().first()
        order = None if payment else ShopOrder.query.filter_by(provider_reference=ref).with_for_update().first()
        if payment or order:
            row = payment or order
            amount = payment.amount if payment else order.total
            if matches(data, ref, amount, row.currency):
                ids = verify_charge(row)
                db.session.commit()
                dispatch_notifications(ids)
                return jsonify(received=True)
            audit(row, "charge.amount_mismatch")
    db.session.commit()
    return jsonify(received=True)


def audit(row, action, actor=None, details=None):
    db.session.add(AuditLog(actor_id=actor, action=action, entity_type=row.__tablename__,
                            entity_id=row.id, after=details))


def control_for(payment):
    row = PaymentControl.query.filter_by(payment_id=payment.id).with_for_update().first()
    if row is None:
        row = PaymentControl(payment_id=payment.id, refunded=Decimal("0"))
        db.session.add(row)
        db.session.flush()
    return row


def verify_charge(row):
    from flask import abort
    try:
        data = Paystack().verify_transaction(row.provider_reference)["data"]
    except Exception:
        abort(502, description="Verification unavailable")
    booking_payment = isinstance(row, Payment)
    amount = row.amount if booking_payment else row.total
    if not matches(data, row.provider_reference, amount, row.currency):
        audit(row, "charge.verification_mismatch")
        return []
    status = data.get("status")
    if booking_payment:
        if status == "success" and row.status == PaymentStatus.PENDING:
            fees = data.get("fees")
            if type(fees) is int and fees > 0:
                post(row.id, "processing_fee", "processing_expense", "provider_receivable", Decimal(fees)/100, row.currency)
            audit(row, "charge.verified")
            return mark_funded(row, {"reference": row.provider_reference, "status": status})
        if status == "success" and row.status == PaymentStatus.FAILED:
            audit(row, "charge.late_success_review")
        if status in {"failed", "abandoned"} and row.status == PaymentStatus.PENDING:
            row.status = PaymentStatus.FAILED
            control_for(row).booking_claim = None
            audit(row, "charge.failed")
    elif row.status not in {"refunded", "partially_refunded", "paid"}:
        if status == "success":
            fee = row.platform_fee or Decimal("0")
            post(row.id, "shop_collection", "provider_receivable", "shop_proceeds", row.total-fee, row.currency)
            post(row.id, "shop_commission", "provider_receivable", "commission_revenue", fee, row.currency)
            if type(data.get("fees")) is int and data["fees"] > 0:
                post(row.id, "processing_fee", "processing_expense", "provider_receivable", Decimal(data["fees"])/100, row.currency)
            row.status, row.paid_at = "paid", datetime.now(timezone.utc)
            queue_email(row.buyer, "Shop payment confirmed", f"We received {row.currency} {row.total:.2f} for order {row.reference}.")
            audit(row, "charge.verified")
        elif status in {"failed","abandoned"}:
            row.status = "payment_failed"
    return []


@bp.post("/payments/<payment_id>/verify")
@role_required(Role.CUSTOMER, Role.ADMIN)
def verify_booking_payment(payment_id):
    query = Payment.query.filter_by(id=payment_id)
    if current_user().role != Role.ADMIN:
        query = query.filter_by(customer_id=current_user().id)
    payment = query.with_for_update().first_or_404()
    ids = verify_charge(payment)
    db.session.commit()
    dispatch_notifications(ids)
    return jsonify(status=payment.status.value)


@bp.post("/bookings/<booking_id>/release")
@role_required(Role.CUSTOMER, Role.ADMIN)
def release_payment(booking_id):
    user = current_user(); booking = Booking.query.filter_by(id=booking_id).with_for_update().first_or_404()
    if user.role != Role.ADMIN and booking.customer_id != user.id: return jsonify({"message": "Booking not found"}), 404
    if os.getenv("PAYMENT_RELEASE_MODE", "customer") not in ({"customer", "admin"} if user.role == Role.ADMIN else {"customer"}):
        return jsonify(message="Release requires administrator approval"), 403
    if booking.status == BookingStatus.DISPUTED and user.role == Role.ADMIN:
        dispute = Dispute.query.filter_by(booking_id=booking.id).order_by(Dispute.created_at.desc()).first()
        decision = AuditLog.query.filter_by(entity_type="dispute", entity_id=dispute.id, action="dispute.decision").order_by(AuditLog.created_at.desc()).first() if dispute else None
        split_ready = False
        if decision and decision.after.get("decision") == "split" and decision.after.get("refund_amount"):
            refunded = db.session.query(db.func.sum(PaymentControl.refunded)).join(Payment,Payment.id==PaymentControl.payment_id).filter(Payment.booking_id==booking.id).scalar()
            split_ready = refunded == Decimal(decision.after["refund_amount"])
        if not decision or (decision.after.get("decision") != "release_to_artisan" and not split_ready):
            return jsonify(message="A release decision is required"), 409
    elif booking.status != BookingStatus.COMPLETION_SUBMITTED: return jsonify({"message": "Artisan must submit completion before release"}), 409
    return complete_release(booking, user.id)


def complete_release(booking, actor_id):
    stages = installments(booking)
    if any(s["status"] in {"unpaid", "pending"} for s in stages):
        return jsonify(message="Complete the agreed payment schedule before release"), 409
    payments = Payment.query.filter_by(booking_id=booking.id, status=PaymentStatus.HELD).order_by(Payment.id).with_for_update().all()
    if not payments:
        return jsonify(message="No held payments to release"), 409
    total = sum(release_installment(booking, payment, actor_id) for payment in payments)
    before = booking.status.value
    booking.status, booking.completed_at = BookingStatus.COMPLETED, datetime.now(timezone.utc)
    db.session.add(BookingStatusEvent(booking_id=booking.id, actor_id=actor_id, from_status=before,
                                      to_status=booking.status.value, note="Payment release approved"))
    db.session.commit()
    return jsonify(booking=booking.public(), released_amount=float(total), currency=booking.currency)


def release_installment(booking, payment, actor_id):
    artisan = ArtisanProfile.query.get(payment.artisan_id); customer_wallet = wallet_for(payment.customer_id, payment.currency); artisan_wallet = wallet_for(artisan.user_id, payment.currency)
    control = control_for(payment)
    if control.provider_hold or RiskEvent.query.filter_by(payment_id=payment.id).filter(RiskEvent.decision.in_(["review","block"])).first() or Dispute.query.filter_by(booking_id=booking.id, status="open").first() or PaymentOperation.query.filter_by(payment_id=payment.id, status="pending").first():
        abort(409, description="Financial review is pending")
    gross = payment.amount - control.refunded
    net = (gross * (payment.amount - payment.platform_fee) / payment.amount).quantize(Decimal("0.01"))
    if customer_wallet.held_balance < gross: abort(409, description="Payment ledger requires reconciliation")
    customer_wallet.held_balance -= gross; artisan_wallet.available_balance += net
    db.session.add(LedgerEntry(account_id=customer_wallet.id, payment_id=payment.id, booking_id=booking.id, direction="debit", bucket="held", amount=gross, currency=payment.currency, event_type="payment_released"))
    db.session.add(LedgerEntry(account_id=artisan_wallet.id, payment_id=payment.id, booking_id=booking.id, direction="credit", bucket="available", amount=net, currency=payment.currency, event_type="job_earning"))
    post(payment.id, "release", "booking_liability", "artisan_payable", net, payment.currency)
    post(payment.id, "commission", "booking_liability", "commission_revenue", gross-net, payment.currency)
    audit(payment, "payment.released", actor_id, {"gross": str(gross), "commission": str(gross-net)})
    payment.status, payment.released_at = PaymentStatus.RELEASED, datetime.now(timezone.utc)
    if enabled("PAYMENT_AUTO_PAYOUT_ENABLED"):
        enqueue("auto_payout", payment.id)
    return net

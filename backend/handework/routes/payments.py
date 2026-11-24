import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from ..extensions import db, limiter
from ..models import ArtisanProfile, Booking, BookingStatus, BookingStatusEvent, LedgerEntry, Payment, PaymentStatus, RiskEvent, Role, ShopOrder, WalletAccount
from ..security import current_user, role_required
from ..services.paystack import Paystack
from ..services.risk import payment_risk
from ..services.notifications import dispatch_notifications, queue_notifications

bp = Blueprint("payments", __name__)


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
    db.session.add(LedgerEntry(account_id=customer_wallet.id, payment_id=payment.id, booking_id=booking.id, direction="credit", bucket="held", amount=payment.amount, currency=payment.currency, event_type="escrow_funded", external_reference=payment.provider_reference))
    if booking.status == BookingStatus.ACCEPTED:
        before = booking.status.value; booking.status = BookingStatus.FUNDED
        db.session.add(BookingStatusEvent(booking_id=booking.id, actor_id=booking.customer_id, from_status=before, to_status=booking.status.value, note="Payment confirmed and held"))
    recipients=[booking.customer]
    if booking.artisan: recipients.append(booking.artisan.user)
    ids=[]
    for recipient in recipients: ids.extend(queue_notifications(recipient,"Payment secured",f"{payment.currency} {float(payment.amount):.2f} is held for {booking.reference}.",{"booking_id":booking.id,"payment_id":payment.id},urgent=True))
    return ids


@bp.post("/payments/mobile-money")
@role_required(Role.CUSTOMER)
@limiter.limit("5 per minute")
def mobile_money():
    user = current_user(); data = request.get_json(silent=True) or {}; booking = Booking.query.filter_by(id=data.get("booking_id"), customer_id=user.id).with_for_update().first_or_404()
    if booking.status != BookingStatus.ACCEPTED or booking.agreed_amount is None: return jsonify({"message": "Accept an artisan quote before payment", "code": "booking_not_payable"}), 409
    idem = request.headers.get("Idempotency-Key") or data.get("idempotency_key")
    if not idem: return jsonify({"message": "Idempotency-Key is required", "code": "missing_idempotency_key"}), 400
    existing = Payment.query.filter_by(idempotency_key=idem).first()
    if existing:
        if existing.customer_id != user.id or existing.booking_id != booking.id: return jsonify({"message": "Idempotency key is already in use", "code": "idempotency_conflict"}), 409
        return jsonify({"payment_id": existing.id, "reference": existing.provider_reference, "status": existing.status.value})
    pending = Payment.query.filter_by(booking_id=booking.id, status=PaymentStatus.PENDING).first()
    if pending:
        return jsonify({"payment_id":pending.id, "reference":pending.provider_reference, "status":"pending"}), 202
    phone, network = str(data.get("phone") or user.phone), str(data.get("network") or "")
    score, signals = payment_risk(user, booking.agreed_amount, phone, network)
    reference = f"handEwork-{secrets.token_hex(8).upper()}"
    fee_bps = int(os.getenv("PLATFORM_FEE_BPS", "1200")); fee = (Decimal(booking.agreed_amount) * fee_bps / Decimal(10000)).quantize(Decimal("0.01"))
    payment = Payment(booking_id=booking.id, customer_id=user.id, artisan_id=booking.artisan_id, provider_reference=reference, idempotency_key=idem, channel="mobile_money", network=network, amount=booking.agreed_amount, platform_fee=fee, currency=booking.currency)
    db.session.add(payment); db.session.flush(); db.session.add(RiskEvent(user_id=user.id, booking_id=booking.id, payment_id=payment.id, kind="payment_initiation", score=score, signals=signals, decision="block" if score >= 90 else "review" if score >= 60 else "allow"))
    if score >= 90: payment.status = PaymentStatus.FAILED; db.session.commit(); return jsonify({"message": "Payment requires manual review", "code": "risk_hold"}), 409
    if not os.getenv("PAYSTACK_SECRET_KEY"):
        db.session.rollback()
        return jsonify({"message": "Mobile money is unavailable right now."}), 503
    db.session.commit()
    try: provider = Paystack().mobile_money_charge(email=user.email, amount_ghs=booking.agreed_amount, phone=phone, network=network, reference=reference)
    except ValueError as error: payment.status = PaymentStatus.FAILED; db.session.commit(); return jsonify({"message": str(error), "code": "unsupported_network"}), 422
    except Exception: db.session.rollback(); return jsonify({"message": "Payment confirmation is unavailable. Check the booking before trying again.", "code": "provider_unavailable"}), 502
    payment.provider_payload = provider; db.session.commit()
    return jsonify({"payment_id": payment.id, "reference": reference, "status": payment.status.value, "provider": provider.get("data", {})}), 202


@bp.post("/webhooks/paystack")
@limiter.exempt
def paystack_webhook():
    raw = request.get_data(); signature = request.headers.get("x-paystack-signature", "")
    try: valid = Paystack().verify_signature(raw, signature)
    except Exception: return jsonify({"message": "Payment webhook is not configured"}), 503
    if not valid: return jsonify({"message": "Invalid signature"}), 401
    payload = request.get_json(silent=True) or {}; event, data = payload.get("event"), payload.get("data", {}); reference = data.get("reference")
    if not reference: return jsonify({"received": True})
    payment = Payment.query.filter_by(provider_reference=reference).with_for_update().first()
    if not payment:
        shop_order = ShopOrder.query.filter_by(provider_reference=reference).with_for_update().first()
        if not shop_order:
            return jsonify({"received": True})
        if shop_order.status == "refunded": return jsonify({"received": True})
        if event in ("charge.success", "charge.successful") and data.get("status") == "success":
            expected_amount = int(round(float(shop_order.total) * 100))
            if data.get("amount") == expected_amount and data.get("currency") == shop_order.currency:
                if shop_order.status != "paid":
                    shop_order.status = "paid"
                    shop_order.paid_at = datetime.now(timezone.utc)
                shop_order.provider_payload = payload
            else:
                shop_order.status = "payment_review"
                shop_order.provider_payload = payload
        elif event in ("charge.failed", "charge.abandoned") and shop_order.status == "pending_payment":
            shop_order.status = "payment_failed"
            shop_order.provider_payload = payload
        elif event == "refund.processed":
            shop_order.status = "refunded"
            shop_order.provider_payload = payload
        db.session.commit()
        return jsonify({"received": True})
    notification_ids=[]
    if event in ("charge.success", "charge.successful") and data.get("status") == "success":
        expected_amount = int(round(float(payment.amount) * 100))
        if data.get("amount") != expected_amount or data.get("currency") != payment.currency:
            db.session.add(RiskEvent(user_id=payment.customer_id, booking_id=payment.booking_id, payment_id=payment.id, kind="webhook_amount_mismatch", score=100, signals={"expected_amount": expected_amount, "received_amount": data.get("amount"), "expected_currency": payment.currency, "received_currency": data.get("currency")}, decision="block"))
            payment.provider_payload = payload
        else: notification_ids=mark_funded(payment, payload)
    elif event in ("charge.failed", "charge.abandoned") and payment.status == PaymentStatus.PENDING: payment.status, payment.provider_payload = PaymentStatus.FAILED, payload
    elif event == "refund.processed": payment.status, payment.refunded_at, payment.provider_payload = PaymentStatus.REFUNDED, datetime.now(timezone.utc), payload
    db.session.commit();dispatch_notifications(notification_ids);return jsonify({"received": True})


@bp.post("/bookings/<booking_id>/release")
@role_required(Role.CUSTOMER, Role.ADMIN)
def release_escrow(booking_id):
    user = current_user(); booking = Booking.query.with_for_update().get_or_404(booking_id)
    if user.role != Role.ADMIN and booking.customer_id != user.id: return jsonify({"message": "Booking not found"}), 404
    if booking.status != BookingStatus.COMPLETION_SUBMITTED: return jsonify({"message": "Artisan must submit completion before release"}), 409
    payment = Payment.query.filter_by(booking_id=booking.id, status=PaymentStatus.HELD).with_for_update().first_or_404()
    artisan = ArtisanProfile.query.get(payment.artisan_id); customer_wallet = wallet_for(payment.customer_id, payment.currency); artisan_wallet = wallet_for(artisan.user_id, payment.currency)
    net = payment.amount - payment.platform_fee
    if customer_wallet.held_balance < payment.amount: return jsonify({"message": "Escrow ledger requires reconciliation", "code": "ledger_mismatch"}), 409
    customer_wallet.held_balance -= payment.amount; artisan_wallet.available_balance += net
    db.session.add(LedgerEntry(account_id=customer_wallet.id, payment_id=payment.id, booking_id=booking.id, direction="debit", bucket="held", amount=payment.amount, currency=payment.currency, event_type="escrow_released"))
    db.session.add(LedgerEntry(account_id=artisan_wallet.id, payment_id=payment.id, booking_id=booking.id, direction="credit", bucket="available", amount=net, currency=payment.currency, event_type="job_earning"))
    payment.status, payment.released_at = PaymentStatus.RELEASED, datetime.now(timezone.utc); before = booking.status.value; booking.status, booking.completed_at = BookingStatus.COMPLETED, datetime.now(timezone.utc)
    db.session.add(BookingStatusEvent(booking_id=booking.id, actor_id=user.id, from_status=before, to_status=booking.status.value, note="Customer approved work and released payment")); db.session.commit()
    return jsonify({"booking": booking.public(), "released_amount": float(net), "currency": payment.currency})


@bp.post("/payments/<payment_id>/refund")
@role_required(Role.ADMIN)
def refund(payment_id):
    payment = Payment.query.with_for_update().get_or_404(payment_id)
    if payment.status not in (PaymentStatus.HELD, PaymentStatus.RELEASED): return jsonify({"message": "Payment cannot be refunded from its current state"}), 409
    data = request.get_json(silent=True) or {}; amount = Decimal(str(data.get("amount") or payment.amount))
    if amount <= 0 or amount > payment.amount: return jsonify({"message": "Invalid refund amount"}), 422
    try: provider = Paystack().refund(payment.provider_reference, amount)
    except Exception: return jsonify({"message": "Refund could not be submitted to the provider"}), 502
    payment.status, payment.provider_payload = PaymentStatus.REFUND_PENDING, provider; db.session.commit(); return jsonify({"status": payment.status.value}), 202

"""Paystack financial operations. Persist intent before each provider write."""
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from flask import abort, jsonify, request
from sqlalchemy.exc import IntegrityError
from ..extensions import db, limiter
from ..models import (ArtisanProfile, AuditLog, Dispute, LedgerEntry, Payment, PaymentControl,
                      PaymentOperation, PaymentStatus, PayoutRecipient, Role, ShopOrder)
from ..models import RiskEvent, ProviderDispute, JournalPosting, PaymentJob
from ..security import current_user, role_required
from ..services.payment_jobs import enqueue
from ..services.journal import post
from ..services.paystack import Paystack, checkout_enabled, enabled, matches, minor
from .payments import audit, bp, control_for, wallet_for


def remote(method, path, **kwargs):
    try:
        return Paystack().call(method, path, **kwargs)["data"]
    except Exception:
        abort(502, description="Paystack response unavailable. Reconcile the existing reference.")


def lock_payment(payment_id):
    return Payment.query.filter_by(id=payment_id).populate_existing().with_for_update().first_or_404()


def net(payment, gross):
    return (gross * (payment.amount - payment.platform_fee) / payment.amount).quantize(Decimal("0.01"))


def movement(wallet, payment, operation, bucket, delta, event):
    column = bucket + "_balance"
    balance = getattr(wallet, column) + delta
    if balance < 0:
        abort(409, description="Insufficient internal balance for reconciliation")
    setattr(wallet, column, balance)
    if delta:
        db.session.add(LedgerEntry(account_id=wallet.id, booking_id=payment.booking_id, payment_id=payment.id,
                                  direction="credit" if delta > 0 else "debit", bucket=bucket, amount=abs(delta),
                                  currency=payment.currency, event_type=event, external_reference=operation.id))


@bp.post("/artisan/payout-recipient")
@role_required(Role.ARTISAN)
@limiter.limit("5 per hour")
def register_recipient():
    user = current_user()
    profile = ArtisanProfile.query.filter_by(user_id=user.id, verification_status="approved").with_for_update().first_or_404()
    data = request.get_json(silent=True) or {}
    if not user.check_password(str(data.get("password", ""))):
        abort(403)
    number, bank, kind = (str(data.get(k, "")) for k in ("account_number", "bank_code", "type"))
    if not re.fullmatch(r"[0-9]{8,18}", number) or not re.fullmatch(r"[A-Za-z0-9_-]{2,12}", bank) or kind not in {"ghipss", "mobile_money"}:
        abort(422)
    resolved = remote("GET", "/bank/resolve", params={"account_number": number, "bank_code": bank})
    name = str(resolved.get("account_name") or "").strip()
    if (resolved.get("account_number") != number or
            name.casefold().split() != f"{user.first_name} {user.last_name}".casefold().split()):
        abort(409, description="Provider account ownership could not be verified")
    recipient = remote("POST", "/transferrecipient", json={"name": name, "type": kind, "currency": "GHS",
                                                          "account_number": number, "bank_code": bank})
    details = recipient.get("details") or {}
    code = recipient.get("recipient_code") or ""
    if (not re.fullmatch(r"RCP_[A-Za-z0-9]+", code) or recipient.get("active") is not True
            or recipient.get("currency") != "GHS" or details.get("account_number") != number
            or details.get("bank_code") != bank):
        abort(409, description="Recipient details require verification")
    row = db.session.get(PayoutRecipient, profile.id) or PayoutRecipient(artisan_id=profile.id)
    row.code, row.last_four = code, number[-4:]
    db.session.add(row)
    audit(profile, "recipient.verified", user.id, {"last_four": row.last_four})
    db.session.commit()
    return jsonify(last_four=row.last_four, status="verified")


@bp.post("/payments/<payment_id>/settlement")
@role_required(Role.ADMIN)
def settlement(payment_id):
    payment = lock_payment(payment_id)
    data = request.get_json(silent=True) or {}
    batch = str(data.get("settlement_id", ""))
    if not batch.isdigit():
        abort(422)
    # Operators can locate large batches by page. Both provider lists must match.
    try:
        batch_page, tx_page = [max(1, int(data.get(key, 1))) for key in ("batch_page", "transaction_page")]
    except (TypeError, ValueError):
        abort(422)
    batches = remote("GET", "/settlement", params={"status": "success", "page": batch_page, "perPage": 100})
    if not any(str(b.get("id")) == batch and b.get("status") == "success" for b in batches):
        abort(409, description="Successful settlement batch not found")
    rows = remote("GET", f"/settlement/{batch}/transactions", params={"page": tx_page, "perPage": 100})
    if not any(matches(r, payment.provider_reference, payment.amount, payment.currency) for r in rows):
        abort(409, description="Charge not found in settlement")
    record_settlement(payment, batch, rows, current_user().id)
    db.session.commit()
    return jsonify(settlement_id=batch)


def record_settlement(payment, batch, rows, actor_id):
    control = control_for(payment)
    if control.settlement_id and control.settlement_id != batch:
        abort(409, description="Conflicting settlement assignment")
    if not control.settlement_id:
        txn = next(r for r in rows if r.get("reference") == payment.provider_reference)
        fees = txn.get("fees")
        if type(fees) is not int or not 0 <= fees <= minor(payment.amount):
            abort(409, description="Settlement fee requires reconciliation")
        post(payment.id, "settlement", "merchant_settlement", "provider_receivable",
             payment.amount - Decimal(fees)/100, payment.currency)
    control.settlement_id = batch
    audit(payment, "settlement.verified", actor_id, {"batch": batch})


def operation_view(op):
    return {"id": op.id, "kind": op.kind, "payment_id": op.payment_id or op.shop_order_id, "amount": str(op.amount),
            "status": op.status, "provider_id": op.provider_id}


@bp.post("/payments/<payment_id>/refund")
@bp.post("/payments/<payment_id>/payout")
@role_required(Role.ADMIN)
def submit_operation(payment_id):
    kind = request.path.rsplit("/", 1)[1]
    if not current_user().check_password(str((request.get_json(silent=True) or {}).get("password", ""))):
        abort(403, description="Confirm your administrator password")
    from ..models import Booking
    booking=db.get_or_404(Booking,lock_payment(payment_id).booking_id)
    if not checkout_enabled(booking.customer, booking) or (kind == "payout" and not enabled("PAYSTACK_TRANSFERS_ENABLED")):
        abort(503, description="Financial operations are disabled")
    return start_operation(payment_id, kind, request.headers.get("Idempotency-Key", ""),
                           request.get_json(silent=True) or {}, current_user().id)


def start_operation(payment_id, kind, key, data, actor_id):
    payment = lock_payment(payment_id)
    control = control_for(payment)
    if not 1 <= len(key) <= 100:
        abort(400, description="Idempotency-Key required")
    previous = PaymentOperation.query.filter_by(request_key=key).with_for_update().first()
    gross = payment.amount - control.refunded
    try:
        amount = Decimal(str(data.get("amount", previous.amount if previous else (gross if kind == "refund" else net(payment, gross)))))
        if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal("0.01")):
            abort(422)
    except (InvalidOperation, ValueError):
        abort(422)
    if previous:
        if (previous.kind, previous.payment_id, previous.amount) != (kind, payment.id, amount):
            abort(409)
        return jsonify(operation_view(previous))
    operations = PaymentOperation.query.filter_by(payment_id=payment.id).with_for_update().all()
    transferred = any(o.kind=="payout" and o.status=="success" for o in operations)
    merchant_refund = transferred and kind=="refund" and data.get("merchant_funded") is True
    if any(o.status == "pending" for o in operations) or (transferred and not merchant_refund):
        abort(409, description="Reconcile existing operation before initiating another")
    if control.provider_hold or payment.status not in {PaymentStatus.HELD, PaymentStatus.RELEASED} or amount > gross:
        abort(409, description="Payment is unavailable for this operation")
    op = PaymentOperation(payment_id=payment.id, kind=kind, amount=amount, request_key=key)
    if kind == "payout":
        if (RiskEvent.query.filter_by(payment_id=payment.id).filter(RiskEvent.decision.in_(["review","block"])).first() or payment.status != PaymentStatus.RELEASED or not control.settlement_id or amount != net(payment, gross)
                or Dispute.query.filter_by(booking_id=payment.booking_id, status="open").first()):
            abort(409, description="Payout requires release, confirmed settlement and cleared disputes")
        recipient = PayoutRecipient.query.filter_by(artisan_id=payment.artisan_id).with_for_update().first_or_404()
        artisan = db.session.get(ArtisanProfile, payment.artisan_id)
        if not artisan or artisan.verification_status != "approved":
            abort(409, description="Artisan verification requires review")
        op.recipient = recipient.code
    db.session.add(op)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Idempotency key already claimed")
    if kind == "payout":
        artisan = db.session.get(ArtisanProfile, payment.artisan_id)
        post(op.id, "reserve", "artisan_payable", "pending_payout", amount, payment.currency)
        movement(wallet_for(artisan.user_id, payment.currency), payment, op, "available", -amount, "transfer_reserved")
    enqueue("verify_operation", op.id)
    audit(op, kind + ".requested", actor_id, {"merchant_funded": bool(merchant_refund)})
    db.session.commit()
    if kind == "refund":
        result = remote("POST", "/refund", json={"transaction": payment.provider_reference, "amount": minor(amount),
                                                "currency": payment.currency, "merchant_note": op.id, "reference": op.id})
        provider_id = str(result.get("id", ""))
        if not provider_id.isdigit():
            abort(502)
        lock_payment(payment_id)
        op.provider_id = provider_id
    else:
        result = remote("POST", "/transfer", json={"source": "balance", "amount": minor(amount), "currency": payment.currency,
                        "recipient": op.recipient, "reference": op.id, "reason": "handEwork artisan payout"})
        if result.get("reference") != op.id:
            abort(502)
    db.session.commit()
    return jsonify(operation_view(op)), 202


def reconcile(op, refund_id=None):
    shop = ShopOrder.query.filter_by(id=op.shop_order_id).with_for_update().first_or_404() if op.shop_order_id else None
    payment = shop or lock_payment(op.payment_id)
    op = PaymentOperation.query.filter_by(id=op.id).populate_existing().with_for_update().one()
    control = None if shop else control_for(payment)
    if op.kind == "refund":
        if op.status != "pending":
            return op
        provider_id = op.provider_id or str(refund_id or "")
        if not provider_id.isdigit():
            candidates = remote("GET", "/refund", params={"reference": payment.provider_reference})
            found = [r for r in candidates if r.get("merchant_note") == op.id]
            if len(found) == 1:
                provider_id = str(found[0].get("id", ""))
        if not provider_id.isdigit():
            abort(409, description="Supply the Paystack refund ID to resolve an uncertain submission")
        data = remote("GET", "/refund/" + provider_id)
        tx = data.get("transaction")
        if isinstance(tx, dict):
            reference = tx.get("reference")
        else:
            charge = remote("GET", "/transaction/verify/" + payment.provider_reference)
            reference = charge.get("reference") if tx and str(charge.get("id")) == str(tx) else None
        if (str(data.get("id")) != provider_id or reference != payment.provider_reference or data.get("merchant_note") != op.id
                or data.get("amount") != minor(op.amount) or data.get("currency") != payment.currency):
            abort(409, description="Refund identity mismatch")
        op.provider_id = provider_id
        status = data.get("status")
        if status == "processed":
            if shop:
                prior = sum(o.amount for o in PaymentOperation.query.filter_by(shop_order_id=shop.id, kind="refund",status="success").with_for_update())
                remaining = shop.total-prior
                if remaining < op.amount:
                    abort(409)
                fee = shop.platform_fee or Decimal("0")
                commission_back = (remaining*fee/shop.total).quantize(Decimal(".01")) - ((remaining-op.amount)*fee/shop.total).quantize(Decimal(".01"))
                post(op.id, "shop_refund", "shop_proceeds", "merchant_funds", op.amount-commission_back, shop.currency)
                post(op.id, "refund_commission", "commission_revenue", "merchant_funds", commission_back, shop.currency)
                shop.status = "refunded" if remaining == op.amount else "partially_refunded"
                op.status = "success"
                audit(op, "refund.reconciled", details={"status":op.status})
                return op
            remaining = payment.amount - control.refunded
            if op.amount > remaining:
                abort(409)
            instruction = AuditLog.query.filter_by(entity_type="payment_operations",entity_id=op.id,action="refund.requested").first()
            if instruction and (instruction.after or {}).get("merchant_funded"):
                fee_back = op.amount - (net(payment, remaining) - net(payment, remaining-op.amount))
                post(op.id, "refund_commission", "commission_revenue", "merchant_funds", fee_back, payment.currency)
                post(op.id, "merchant_refund", "merchant_refund_expense", "merchant_funds", op.amount-fee_back, payment.currency)
            elif payment.status == PaymentStatus.RELEASED:
                artisan = db.session.get(ArtisanProfile, payment.artisan_id)
                deduction = net(payment, remaining) - net(payment, remaining - op.amount)
                post(op.id, "refund_net", "artisan_payable", "merchant_funds", deduction, payment.currency)
                post(op.id, "refund_commission", "commission_revenue", "merchant_funds", op.amount-deduction, payment.currency)
                movement(wallet_for(artisan.user_id, payment.currency), payment, op, "available", -deduction, "refund_reconciled")
            elif payment.status == PaymentStatus.HELD:
                post(op.id, "refund", "booking_liability", "merchant_funds", op.amount, payment.currency)
                movement(wallet_for(payment.customer_id, payment.currency), payment, op, "held", -op.amount, "refund_reconciled")
            else:
                abort(409)
            control.refunded += op.amount
            if control.refunded == payment.amount:
                payment.status, payment.refunded_at = PaymentStatus.REFUNDED, datetime.now(timezone.utc)
            op.status = "success"
        elif status == "failed":
            op.status = "failed"
    else:
        data = remote("GET", "/transfer/verify/" + op.id)
        recipient = data.get("recipient") or {}
        if not matches(data, op.id, op.amount, payment.currency) or recipient.get("recipient_code") != op.recipient:
            abort(409, description="Transfer identity mismatch")
        status = data.get("status")
        if status == "success" and op.status == "pending":
            post(op.id, "transferred", "pending_payout", "merchant_funds", op.amount, payment.currency)
            fee = data.get("fee_charged")
            if type(fee) is int and fee > 0:
                post(op.id, "transfer_fee", "payout_expense", "merchant_funds", Decimal(fee)/100, payment.currency)
            op.status = "success"
        elif ((status in {"failed", "reversed"} and op.status == "pending") or
              (status == "reversed" and op.status == "success")):
            artisan = db.session.get(ArtisanProfile, payment.artisan_id)
            post(op.id, "returned", "merchant_funds" if op.status == "success" else "pending_payout", "artisan_payable", op.amount, payment.currency)
            movement(wallet_for(artisan.user_id, payment.currency), payment, op, "available", op.amount, "transfer_returned")
            op.status = status
    audit(op, op.kind + ".reconciled", details={"status": op.status})
    return op


def reconcile_event(event, data):
    if event.startswith("transfer."):
        op = PaymentOperation.query.filter_by(kind="payout", id=data.get("reference")).first()
    else:
        op = PaymentOperation.query.filter_by(kind="refund", provider_id=str(data.get("id"))).first()
        if not op and data.get("merchant_note"):
            op = PaymentOperation.query.filter_by(kind="refund", id=data["merchant_note"]).first()
    if op:
        reconcile(op, data.get("id"))
    else:
        db.session.add(AuditLog(action="provider.unmatched", entity_type="payment_operations",
                               after={"event": event, "provider_id": str(data.get("id", ""))[:100]}))


@bp.post("/admin/payment-operations/<op_id>/reconcile")
@role_required(Role.ADMIN)
def reconcile_operation(op_id):
    op = reconcile(PaymentOperation.query.get_or_404(op_id), (request.get_json(silent=True) or {}).get("refund_id"))
    db.session.commit()
    return jsonify(operation_view(op))


@bp.get("/admin/payment-operations")
@role_required(Role.ADMIN)
def operations():
    payments = Payment.query.order_by(Payment.created_at.desc()).limit(200).all()
    controls = {c.payment_id: c for c in PaymentControl.query.filter(PaymentControl.payment_id.in_([p.id for p in payments])).all()}
    rows = []
    for payment in payments:
        control = controls.get(payment.id)
        rows.append({"id": payment.id, "reference": payment.provider_reference, "amount": str(payment.amount),
                     "currency": payment.currency, "status": payment.status.value,
                     "settlement": control.settlement_id if control and control.settlement_id else "unconfirmed",
                     "refunded": str(control.refunded) if control else "0"})
    history = AuditLog.query.filter(AuditLog.entity_type.in_(["payments", "payment_operations", "shop_orders", "artisan_profiles", "dispute"])).order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify(payments=rows, orders=[{"id":o.id,"reference": o.reference, "amount": str(o.total), "status": o.status} for o in ShopOrder.query.order_by(ShopOrder.created_at.desc()).limit(200)],
                   operations=[operation_view(o) for o in PaymentOperation.query.order_by(PaymentOperation.created_at.desc()).limit(200)],
                   audit=[{"id": h.id, "action": h.action, "record": h.entity_id, "actor": h.actor_id, "at": h.created_at.isoformat()} for h in history])

@bp.get("/artisan/payouts")
@role_required(Role.ARTISAN)
def artisan_payouts():
    artisan = ArtisanProfile.query.filter_by(user_id=current_user().id).first_or_404()
    ops = PaymentOperation.query.join(Payment, PaymentOperation.payment_id == Payment.id).filter(
        Payment.artisan_id == artisan.id, PaymentOperation.kind == "payout").order_by(PaymentOperation.created_at.desc()).limit(200).all()
    payments = Payment.query.filter_by(artisan_id=artisan.id, status=PaymentStatus.RELEASED).order_by(Payment.created_at.desc()).limit(200).all()
    recipient = db.session.get(PayoutRecipient, artisan.id)
    return jsonify(last_four=recipient.last_four if recipient else None, operations=[operation_view(o) for o in ops],
                   earnings=[{"id":p.id, "reference":p.provider_reference, "currency":p.currency,
                              "net":str(net(p,p.amount-(c.refunded if c else 0))),
                              "settlement":c.settlement_id if c else None}
                             for p in payments for c in [db.session.get(PaymentControl,p.id)]])


@bp.get("/artisan/payout-institutions")
@role_required(Role.ARTISAN)
def payout_institutions():
    kind = request.args.get("type", "ghipss")
    if kind not in {"ghipss","mobile_money"}:
        abort(422)
    rows = remote("GET","/bank",params={"country":"ghana","currency":"GHS","type":kind,"perPage":100})
    return jsonify(items=[{"code":r["code"], "name":r["name"]} for r in rows if r.get("active",True)])


@bp.post("/artisan/earnings/<payment_id>/withdraw")
@role_required(Role.ARTISAN)
@limiter.limit("10 per hour")
def withdraw(payment_id):
    if not enabled("PAYMENTS_ENABLED") or not enabled("PAYSTACK_TRANSFERS_ENABLED"):
        abort(503,description="Transfers are disabled")
    user = current_user()
    profile = ArtisanProfile.query.filter_by(user_id=user.id, verification_status="approved").first_or_404()
    Payment.query.filter_by(id=payment_id, artisan_id=profile.id).first_or_404()
    data = request.get_json(silent=True) or {}
    if not user.check_password(str(data.get("password",""))):
        abort(403)
    return start_operation(payment_id, "payout", request.headers.get("Idempotency-Key",""), {}, user.id)

@bp.post("/admin/shop-orders/<order_id>/refund")
@role_required(Role.ADMIN)
def shop_refund(order_id):
    data = request.get_json(silent=True) or {}
    if not enabled("PAYMENTS_ENABLED"):
        abort(503)
    if not current_user().check_password(str(data.get("password", ""))):
        abort(403)
    shop = ShopOrder.query.filter_by(id=order_id).with_for_update().first_or_404()
    key = request.headers.get("Idempotency-Key", "")
    if not 1 <= len(key) <= 100:
        abort(400)
    try:
        amount = Decimal(str(data["amount"]))
        if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal(".01")):
            abort(422)
    except (InvalidOperation, KeyError):
        abort(422)
    existing = PaymentOperation.query.filter_by(request_key=key).with_for_update().first()
    if existing:
        if existing.shop_order_id != shop.id or existing.amount != amount:
            abort(409)
        return jsonify(operation_view(existing))
    rows = PaymentOperation.query.filter_by(shop_order_id=shop.id).with_for_update().all()
    if shop.status not in {"paid","partially_refunded"} or any(o.status=="pending" for o in rows) or amount > shop.total-sum(o.amount for o in rows if o.status=="success"):
        abort(409)
    op = PaymentOperation(shop_order_id=shop.id, request_key=key, kind="refund", amount=amount)
    db.session.add(op)
    db.session.flush()
    audit(op,"shop_refund.requested", current_user().id)
    enqueue("verify_operation",op.id)
    db.session.commit()
    result = remote("POST","/refund",json={"transaction":shop.provider_reference,"amount":minor(amount),"currency":shop.currency,"reference":op.id,"merchant_note":op.id})
    provider_id = str(result.get("id",""))
    if not provider_id.isdigit():
        abort(502)
    op.provider_id = provider_id
    db.session.commit()
    return jsonify(operation_view(op)),202

def sync_dispute(provider_id, reference):
    if not provider_id.isdigit():
        abort(422)
    payment = Payment.query.filter_by(provider_reference=reference).with_for_update().first()
    row = payment or ShopOrder.query.filter_by(provider_reference=reference).with_for_update().first_or_404()
    data = remote("GET","/dispute/"+provider_id)
    tx = data.get("transaction") or {}
    if str(data.get("id")) != provider_id or not matches(tx, reference, payment.amount if payment else row.total, row.currency):
        abort(409,description="Dispute transaction mismatch")
    dispute = db.session.get(ProviderDispute,provider_id) or ProviderDispute(provider_id=provider_id,reference=reference,deduction_units=0)
    if dispute.reference != reference:
        abort(409)
    dispute.status = str(data.get("status") or "open")[:32]
    dispute.resolution = str(data.get("resolution") or "")[:64]
    db.session.add(dispute)
    # Provider confirms the deduction independently of our recorded merchant response.
    deduction = data.get("refund_amount")
    if dispute.status=="resolved" and dispute.resolution=="merchant-accepted" and type(deduction) is int and deduction>0 and not dispute.deduction_units:
        if deduction > tx["amount"]:
            abort(409)
        post("dispute-"+provider_id, "chargeback_liability", "chargeback_loss", "chargeback_payable", Decimal(deduction)/100, row.currency)
        dispute.deduction_units=deduction
    db.session.flush()
    if payment:
        cases = ProviderDispute.query.filter_by(reference=reference).all()
        control_for(payment).provider_hold = any(c.status!="resolved" or c.resolution!="declined" for c in cases)
    audit(row,"chargeback.reconciled",details={"id":provider_id,"status":dispute.status,"resolution":dispute.resolution})
    return dispute


@bp.post("/admin/payment-disputes/<provider_id>/verify")
@role_required(Role.ADMIN)
def verify_dispute(provider_id):
    row=db.get_or_404(ProviderDispute,provider_id)
    case=sync_dispute(provider_id,row.reference)
    db.session.commit()
    return jsonify(status=case.status)


@bp.get("/admin/payment-summary")
@role_required(Role.ADMIN)
def summary():
    def sum_journal(events):
        return int(db.session.query(db.func.coalesce(db.func.sum(JournalPosting.units),0)).filter(JournalPosting.event.in_(events)).scalar())
    def sum_ops(kind,status):
        return minor(db.session.query(db.func.coalesce(db.func.sum(PaymentOperation.amount),0)).filter_by(kind=kind,status=status).scalar())
    from ..models import WalletAccount
    awaiting = db.session.query(db.func.coalesce(db.func.sum(Payment.amount),0)).outerjoin(PaymentControl,PaymentControl.payment_id==Payment.id).filter(Payment.paid_at.isnot(None),PaymentControl.settlement_id.is_(None)).scalar()
    balances = db.session.query(db.func.coalesce(db.func.sum(WalletAccount.available_balance),0),db.func.coalesce(db.func.sum(WalletAccount.held_balance),0)).filter_by(currency="GHS").one()
    return jsonify(currency="GHS", metrics={
        "Recorded collections":sum_journal(["collection","shop_collection","shop_commission"]),
        "Commission revenue":sum_journal(["commission","shop_commission"])-sum_journal(["refund_commission"]),
        "Processing and payout fees":sum_journal(["processing_fee","transfer_fee"]),
        "Booking collections awaiting settlement":minor(awaiting),
        "Held booking balance":minor(balances[1]),"Available artisan earnings":minor(balances[0]),
        "Pending transfers":sum_ops("payout","pending"),"Successful transfers":sum_ops("payout","success"),
        "Failed transfers":sum_ops("payout","failed"),"Processed refunds":sum_ops("refund","success"),
        "Chargeback liabilities":sum_journal(["chargeback_liability"])},
        chargebacks=[{"id":c.provider_id,"reference":c.reference,"status":c.status,"resolution":c.resolution} for c in ProviderDispute.query.limit(200)],
        discrepancies=[{"id":j.key,"error":j.last_error,"attempts":j.attempts} for j in PaymentJob.query.filter(PaymentJob.last_error.isnot(None)).order_by(PaymentJob.due_at).limit(200)])

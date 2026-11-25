from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid5
from ..models import JobChange, Payment, PaymentControl, PaymentStatus, Quote


def validate_schedule(items, total):
    if items is None:
        return None
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError
    result = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError
        try:
            amount = Decimal(str(item.get("amount")))
            if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal(".01")):
                raise ValueError
        except InvalidOperation as exc:
            raise ValueError from exc
        label = str(item.get("label") or "").strip()
        if not 1 <= len(label) <= 120:
            raise ValueError
        result.append({"label": label, "amount": str(amount)})
    if sum(Decimal(r["amount"]) for r in result) != total:
        raise ValueError
    return result


def installments(booking):
    if not booking.agreed_amount:
        return []
    quote = Quote.query.filter_by(booking_id=booking.id, status="accepted").first()
    schedule = quote.payment_schedule if quote else None
    stages = [{"claim": str(uuid5(UUID(booking.id), str(i))), **row} for i, row in enumerate(schedule or [])]
    if not stages:
        stages = [{"claim": booking.id, "label": "Booking payment", "amount": str(booking.agreed_amount)}]
    for change in JobChange.query.filter_by(booking_id=booking.id, status="approved").order_by(JobChange.created_at, JobChange.id):
        stages.append({"claim": change.id, "label": change.description, "amount": str(change.extra_amount)})
    payments = (Payment.query.outerjoin(PaymentControl, PaymentControl.payment_id == Payment.id)
                .add_entity(PaymentControl).filter(Payment.booking_id == booking.id, Payment.status != PaymentStatus.FAILED).all())
    by_claim = {(control.booking_claim if control and control.booking_claim else booking.id): payment
                for payment, control in payments}
    for row in stages:
        payment = by_claim.get(row["claim"])
        row.update(status=payment.status.value if payment else "unpaid", payment_id=payment.id if payment else None,
                   reference=payment.provider_reference if payment else None)
    return stages

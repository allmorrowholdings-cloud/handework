from datetime import datetime, timedelta, timezone
from ..models import Booking, Payment


def payment_risk(user, amount, phone, network):
    signals, score = {}, 0
    if float(amount) >= 5000: signals["large_amount"] = True; score += 25
    if user.phone != phone: signals["payment_phone_differs"] = True; score += 18
    account_age = datetime.now(timezone.utc) - user.created_at.replace(tzinfo=timezone.utc) if user.created_at.tzinfo is None else datetime.now(timezone.utc) - user.created_at
    if account_age < timedelta(hours=24): signals["new_account"] = True; score += 18
    recent = Payment.query.filter(Payment.customer_id == user.id, Payment.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)).count()
    if recent >= 3: signals["payment_velocity"] = recent; score += min(35, recent * 7)
    cancelled = Booking.query.filter_by(customer_id=user.id).filter(Booking.status.in_(["cancelled", "refunded"])).count()
    if cancelled >= 3: signals["cancellation_history"] = cancelled; score += min(20, cancelled * 3)
    return min(score, 100), signals

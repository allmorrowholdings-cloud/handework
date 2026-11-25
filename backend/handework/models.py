import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from werkzeug.security import check_password_hash, generate_password_hash
from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    CUSTOMER = "customer"
    ARTISAN = "artisan"
    ADMIN = "admin"


class BookingStatus(str, enum.Enum):
    REQUESTED = "requested"
    QUOTED = "quoted"
    ACCEPTED = "accepted"
    FUNDED = "funded"
    EN_ROUTE = "en_route"
    IN_PROGRESS = "in_progress"
    COMPLETION_SUBMITTED = "completion_submitted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    REFUNDED = "refunded"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    HELD = "held"
    RELEASED = "released"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"


class UUIDMixin:
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class User(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(32), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False, default=Role.CUSTOMER, index=True)
    status = db.Column(db.String(24), nullable=False, default="active", index=True)
    email_verified_at = db.Column(db.DateTime(timezone=True))
    phone_verified_at = db.Column(db.DateTime(timezone=True))
    last_login_at = db.Column(db.DateTime(timezone=True))
    locale = db.Column(db.String(12), nullable=False, default="en-GH")
    country_code = db.Column(db.String(2), nullable=False, default="GH", index=True)
    referral_code = db.Column(db.String(20), unique=True, index=True)
    notification_preferences = db.Column(db.JSON, nullable=False, default=lambda: {"push": True, "whatsapp": False, "sms": True})

    def set_password(self, value): self.password_hash = generate_password_hash(value, method="scrypt")
    def check_password(self, value): return check_password_hash(self.password_hash, value)
    def public(self): return {"id": self.id, "email": self.email, "phone": self.phone, "first_name": self.first_name, "last_name": self.last_name, "role": self.role.value, "status": self.status, "country_code": self.country_code, "notification_preferences": self.notification_preferences or {"push": True, "whatsapp": False, "sms": True}}


class LoginSession(UUIDMixin, db.Model):
    __tablename__ = "login_sessions"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    last_active = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ArtisanProfile(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "artisan_profiles"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    display_name = db.Column(db.String(160), nullable=False)
    trade = db.Column(db.String(120), nullable=False, index=True)
    secondary_services = db.Column(db.Text)
    bio = db.Column(db.Text)
    years_experience = db.Column(db.Integer, nullable=False, default=0)
    city = db.Column(db.String(100), nullable=False, index=True)
    area = db.Column(db.String(140), nullable=False)
    latitude = db.Column(db.Numeric(10, 7))
    longitude = db.Column(db.Numeric(10, 7))
    radius_km = db.Column(db.Integer, nullable=False, default=10)
    starting_price = db.Column(db.Numeric(12, 2))
    currency = db.Column(db.String(3), nullable=False, default="GHS")
    languages = db.Column(db.String(255))
    avatar_url = db.Column(db.String(700))
    avatar_file_id = db.Column(db.String(36), db.ForeignKey("file_assets.id", ondelete="SET NULL", use_alter=True, name="fk_artisan_profiles_avatar_file_id"))
    verification_status = db.Column(db.String(24), nullable=False, default="draft", index=True)
    available = db.Column(db.Boolean, nullable=False, default=False, index=True)
    instant_booking = db.Column(db.Boolean, nullable=False, default=False)
    rating_average = db.Column(db.Numeric(3, 2))
    review_count = db.Column(db.Integer, nullable=False, default=0)
    completion_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("0"))
    response_minutes = db.Column(db.Integer)
    user = db.relationship("User", lazy="joined")

    def search_card(self, distance_km):
        return {"id": self.id, "display_name": self.display_name, "trade": self.trade, "rating": float(self.rating_average) if self.rating_average is not None else None, "review_count": self.review_count, "distance_km": round(distance_km, 1) if distance_km is not None else None, "starting_price": float(self.starting_price) if self.starting_price is not None else None, "currency": self.currency, "verified": self.verification_status == "approved", "instant_booking": self.instant_booking, "avatar_url": self.avatar_url, "latitude": round(float(self.latitude), 3) if self.latitude is not None else None, "longitude": round(float(self.longitude), 3) if self.longitude is not None else None}


class PortfolioItem(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "portfolio_items"
    artisan_id = db.Column(db.String(36), db.ForeignKey("artisan_profiles.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text)
    service = db.Column(db.String(120), nullable=False, index=True)
    media_url = db.Column(db.String(700), nullable=False)
    file_asset_id = db.Column(db.String(36), db.ForeignKey("file_assets.id", ondelete="SET NULL"), index=True)
    media_type = db.Column(db.String(24), nullable=False, default="image")
    before_after = db.Column(db.String(12))
    moderation_status = db.Column(db.String(20), nullable=False, default="pending", index=True)


class Availability(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "availability"
    artisan_id = db.Column(db.String(36), db.ForeignKey("artisan_profiles.id"), nullable=False, index=True)
    weekday = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (db.UniqueConstraint("artisan_id", "weekday", name="uq_artisan_weekday"),)


class Booking(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "bookings"
    reference = db.Column(db.String(20), nullable=False, unique=True, index=True)
    customer_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    artisan_id = db.Column(db.String(36), db.ForeignKey("artisan_profiles.id"), index=True)
    service = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    area = db.Column(db.String(140), nullable=False)
    city = db.Column(db.String(100), nullable=False, index=True)
    latitude = db.Column(db.Numeric(10, 7))
    longitude = db.Column(db.Numeric(10, 7))
    scheduled_start = db.Column(db.DateTime(timezone=True))
    scheduled_end = db.Column(db.DateTime(timezone=True))
    budget_type = db.Column(db.String(20), nullable=False, default="quote")
    budget_amount = db.Column(db.Numeric(12, 2))
    agreed_amount = db.Column(db.Numeric(12, 2))
    currency = db.Column(db.String(3), nullable=False, default="GHS")
    contact_phone = db.Column(db.String(32), nullable=False)
    status = db.Column(db.Enum(BookingStatus), nullable=False, default=BookingStatus.REQUESTED, index=True)
    cancellation_reason = db.Column(db.String(500))
    completed_at = db.Column(db.DateTime(timezone=True))
    customer = db.relationship("User", foreign_keys=[customer_id], lazy="joined")
    artisan = db.relationship("ArtisanProfile", foreign_keys=[artisan_id], lazy="joined")

    def public(self):
        return {"id": self.id, "reference": self.reference, "service": self.service, "description": self.description, "area": self.area, "city": self.city, "scheduled_start": self.scheduled_start.isoformat() if self.scheduled_start else None, "budget_type": self.budget_type, "budget_amount": float(self.budget_amount) if self.budget_amount is not None else None, "agreed_amount": float(self.agreed_amount) if self.agreed_amount is not None else None, "currency": self.currency, "status": self.status.value, "artisan": {"id": self.artisan.id, "display_name": self.artisan.display_name, "trade": self.artisan.trade} if self.artisan else None, "created_at": self.created_at.isoformat()}


class BookingStatusEvent(UUIDMixin, db.Model):
    __tablename__ = "booking_status_events"
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), nullable=False, index=True)
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    from_status = db.Column(db.String(32))
    to_status = db.Column(db.String(32), nullable=False)
    note = db.Column(db.String(500))
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class JobChange(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "job_changes"
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), nullable=False, index=True)
    description = db.Column(db.String(500), nullable=False)
    extra_amount = db.Column(db.Numeric(12, 2), nullable=False)
    base_amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")

    def public(self):
        return {"id": self.id, "description": self.description, "extra_amount": str(self.extra_amount),
                "current_total": str(self.base_amount), "new_total": str(self.base_amount + self.extra_amount),
                "status": self.status}


class Quote(UUIDMixin, TimestampMixin, db.Model):
    payment_schedule = db.Column(db.JSON)
    __tablename__ = "quotes"
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), nullable=False, index=True)
    artisan_id = db.Column(db.String(36), db.ForeignKey("artisan_profiles.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="GHS")
    note = db.Column(db.Text)
    valid_until = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(20), nullable=False, default="submitted", index=True)


class Payment(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "payments"
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), nullable=False, index=True)
    customer_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    artisan_id = db.Column(db.String(36), db.ForeignKey("artisan_profiles.id"), index=True)
    provider = db.Column(db.String(30), nullable=False, default="paystack")
    provider_reference = db.Column(db.String(120), nullable=False, unique=True, index=True)
    idempotency_key = db.Column(db.String(100), unique=True, index=True)
    channel = db.Column(db.String(30), nullable=False)
    network = db.Column(db.String(20))
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    platform_fee = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0"))
    currency = db.Column(db.String(3), nullable=False, default="GHS")
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING, index=True)
    provider_payload = db.Column(db.JSON)
    paid_at = db.Column(db.DateTime(timezone=True))
    released_at = db.Column(db.DateTime(timezone=True))
    refunded_at = db.Column(db.DateTime(timezone=True))


class WalletAccount(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "wallet_accounts"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    currency = db.Column(db.String(3), nullable=False, default="GHS")
    available_balance = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    held_balance = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    __table_args__ = (db.UniqueConstraint("user_id", "currency", name="uq_wallet_user_currency"),)


class LedgerEntry(UUIDMixin, db.Model):
    __tablename__ = "ledger_entries"
    account_id = db.Column(db.String(36), db.ForeignKey("wallet_accounts.id"), nullable=False, index=True)
    payment_id = db.Column(db.String(36), db.ForeignKey("payments.id"), index=True)
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), index=True)
    direction = db.Column(db.String(6), nullable=False)
    bucket = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="GHS")
    event_type = db.Column(db.String(40), nullable=False, index=True)
    external_reference = db.Column(db.String(120), index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class Conversation(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "conversations"
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), nullable=False, unique=True, index=True)
    customer_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    artisan_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    last_message_at = db.Column(db.DateTime(timezone=True), index=True)
    closed_at = db.Column(db.DateTime(timezone=True))


class Message(UUIDMixin, db.Model):
    __tablename__ = "messages"
    conversation_id = db.Column(db.String(36), db.ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    body = db.Column(db.Text)
    media_url = db.Column(db.String(700))
    media_type = db.Column(db.String(24))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    edited_at = db.Column(db.DateTime(timezone=True))
    deleted_at = db.Column(db.DateTime(timezone=True))


class Review(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "reviews"
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), nullable=False, unique=True)
    customer_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    artisan_id = db.Column(db.String(36), db.ForeignKey("artisan_profiles.id"), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    moderation_status = db.Column(db.String(20), nullable=False, default="published")


class WorkProofProfile(UUIDMixin, TimestampMixin, db.Model):
    """Portable, derived work reputation. This is not a credit score."""
    __tablename__ = "workproof_profiles"
    artisan_id = db.Column(db.String(36), db.ForeignKey("artisan_profiles.id"), nullable=False, unique=True, index=True)
    score = db.Column(db.Integer, nullable=False, default=0)
    verified_jobs = db.Column(db.Integer, nullable=False, default=0)
    external_verified_jobs = db.Column(db.Integer, nullable=False, default=0)
    repeat_clients = db.Column(db.Integer, nullable=False, default=0)
    completion_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("0"))
    average_rating = db.Column(db.Numeric(3, 2))
    unresolved_disputes = db.Column(db.Integer, nullable=False, default=0)
    years_verified = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("0"))
    last_calculated_at = db.Column(db.DateTime(timezone=True))


class WorkProofEvidence(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "workproof_evidence"
    artisan_id = db.Column(db.String(36), db.ForeignKey("artisan_profiles.id"), nullable=False, index=True)
    evidence_type = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text)
    occurred_at = db.Column(db.DateTime(timezone=True))
    verifier_name = db.Column(db.String(160), nullable=False)
    verifier_contact = db.Column(db.String(254), nullable=False)
    verification_method = db.Column(db.String(40))
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    reviewer_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    decision_reason = db.Column(db.String(500))
    decided_at = db.Column(db.DateTime(timezone=True))
    public_metadata = db.Column(db.JSON, nullable=False, default=dict)
    file_asset_id = db.Column(db.String(36), db.ForeignKey("file_assets.id", ondelete="SET NULL"), index=True)


class Notification(UUIDMixin, db.Model):
    __tablename__ = "notifications"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    channel = db.Column(db.String(20), nullable=False, default="in_app")
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.String(700), nullable=False)
    data = db.Column(db.JSON)
    status = db.Column(db.String(20), nullable=False, default="queued", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    sent_at = db.Column(db.DateTime(timezone=True))
    read_at = db.Column(db.DateTime(timezone=True))


class PushDevice(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "push_devices"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    expo_push_token = db.Column(db.String(255), nullable=False, unique=True)
    platform = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)


class Verification(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "verifications"
    artisan_id = db.Column(db.String(36), db.ForeignKey("artisan_profiles.id"), nullable=False, index=True)
    kind = db.Column(db.String(32), nullable=False)
    file_url = db.Column(db.String(700))
    file_asset_id = db.Column(db.String(36), db.ForeignKey("file_assets.id", ondelete="SET NULL"), index=True)
    status = db.Column(db.String(24), nullable=False, default="pending", index=True)
    provider_reference = db.Column(db.String(120))
    reviewer_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    decision_reason = db.Column(db.String(500))
    decided_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (db.UniqueConstraint("artisan_id", "kind", name="uq_verification_kind"),)


class Dispute(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "disputes"
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), nullable=False, index=True)
    opened_by_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    reason = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(24), nullable=False, default="open", index=True)
    assigned_admin_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    resolution = db.Column(db.Text)
    resolved_at = db.Column(db.DateTime(timezone=True))


class RiskEvent(UUIDMixin, db.Model):
    __tablename__ = "risk_events"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), index=True)
    payment_id = db.Column(db.String(36), db.ForeignKey("payments.id"), index=True)
    kind = db.Column(db.String(60), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)
    signals = db.Column(db.JSON, nullable=False)
    decision = db.Column(db.String(24), nullable=False, default="review", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class PromoCode(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "promo_codes"
    code = db.Column(db.String(40), nullable=False, unique=True, index=True)
    discount_type = db.Column(db.String(20), nullable=False)
    discount_value = db.Column(db.Numeric(12, 2), nullable=False)
    minimum_amount = db.Column(db.Numeric(12, 2))
    currency = db.Column(db.String(3), nullable=False, default="GHS")
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    max_uses = db.Column(db.Integer)
    use_count = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)


class Referral(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "referrals"
    referrer_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    referred_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, unique=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    reward_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0"))
    qualifying_booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"))


class Subscription(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "subscriptions"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    plan = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    provider_reference = db.Column(db.String(120), index=True)
    current_period_start = db.Column(db.DateTime(timezone=True))
    current_period_end = db.Column(db.DateTime(timezone=True))


class Organization(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "organizations"
    name = db.Column(db.String(180), nullable=False)
    country_code = db.Column(db.String(2), nullable=False, default="GH")
    billing_email = db.Column(db.String(254), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")


class OrganizationMember(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "organization_members"
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(30), nullable=False, default="requester")
    spend_limit = db.Column(db.Numeric(14, 2))
    __table_args__ = (db.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),)


class TrainingProvider(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "training_providers"
    name = db.Column(db.String(200), nullable=False)
    institution_type = db.Column(db.String(60), nullable=False)
    country_code = db.Column(db.String(2), nullable=False, default="GH")
    verification_status = db.Column(db.String(20), nullable=False, default="pending")


class Course(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "courses"
    provider_id = db.Column(db.String(36), db.ForeignKey("training_providers.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    trade = db.Column(db.String(120), nullable=False, index=True)
    city = db.Column(db.String(100))
    delivery_mode = db.Column(db.String(30), nullable=False)
    fee = db.Column(db.Numeric(12, 2))
    currency = db.Column(db.String(3), nullable=False, default="GHS")
    enrollment_url = db.Column(db.String(700))
    published = db.Column(db.Boolean, nullable=False, default=False, index=True)


class SupportTicket(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "support_tickets"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), index=True)
    email = db.Column(db.String(254), nullable=False)
    topic = db.Column(db.String(80), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="normal", index=True)
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    assigned_admin_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)


class FileAsset(UUIDMixin, db.Model):
    __tablename__ = "file_assets"
    owner_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    booking_id = db.Column(db.String(36), db.ForeignKey("bookings.id"), index=True)
    purpose = db.Column(db.String(40), nullable=False, index=True)
    url = db.Column(db.String(700), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    storage_bucket = db.Column(db.String(128))
    storage_key = db.Column(db.String(1024))
    original_filename = db.Column(db.String(255))
    size_bytes = db.Column(db.BigInteger)
    sha256 = db.Column(db.String(64))
    is_private = db.Column(db.Boolean, nullable=False, default=True)
    deleted_at = db.Column(db.DateTime(timezone=True))
    replaces_asset_id = db.Column(db.String(36), db.ForeignKey("file_assets.id", ondelete="SET NULL"))
    scan_status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class ShopProductMedia(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "shop_product_media"
    product_id = db.Column(db.String(80), nullable=False, unique=True, index=True)
    file_asset_id = db.Column(db.String(36), db.ForeignKey("file_assets.id", ondelete="RESTRICT"), nullable=False)


class AuditLog(UUIDMixin, db.Model):
    __tablename__ = "audit_logs"
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(60), nullable=False)
    entity_id = db.Column(db.String(36), index=True)
    before = db.Column(db.JSON)
    after = db.Column(db.JSON)
    ip_hash = db.Column(db.String(64))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class ShopOrder(UUIDMixin, TimestampMixin, db.Model):
    platform_fee = db.Column(db.Numeric(12,2))
    __tablename__ = "shop_orders"
    reference = db.Column(db.String(32), nullable=False, unique=True, index=True)
    buyer_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(24), nullable=False, default="pending_payment", index=True)
    currency = db.Column(db.String(3), nullable=False, default="GHS")
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    delivery_fee = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0"))
    total = db.Column(db.Numeric(12, 2), nullable=False)
    fulfilment = db.Column(db.String(16), nullable=False)
    full_name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    area = db.Column(db.String(140))
    address = db.Column(db.String(500))
    pickup_note = db.Column(db.String(500))
    provider_reference = db.Column(db.String(120), unique=True, index=True)
    provider_payload = db.Column(db.JSON)
    paid_at = db.Column(db.DateTime(timezone=True))
    fulfilled_at = db.Column(db.DateTime(timezone=True))
    buyer = db.relationship("User", foreign_keys=[buyer_id], lazy="joined")
    items = db.relationship("ShopOrderItem", backref="order", cascade="all, delete-orphan", lazy="selectin")

    def public(self):
        return {
            "id": self.id,
            "reference": self.reference,
            "status": self.status,
            "currency": self.currency,
            "subtotal": float(self.subtotal),
            "delivery_fee": float(self.delivery_fee),
            "total": float(self.total),
            "fulfilment": self.fulfilment,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "area": self.area,
            "address": self.address,
            "pickup_note": self.pickup_note,
            "provider_reference": self.provider_reference,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat(),
            "items": [item.public() for item in self.items],
        }


class ShopOrderItem(UUIDMixin, db.Model):
    __tablename__ = "shop_order_items"
    order_id = db.Column(db.String(36), db.ForeignKey("shop_orders.id"), nullable=False, index=True)
    product_id = db.Column(db.String(80), nullable=False, index=True)
    product_name = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    line_total = db.Column(db.Numeric(12, 2), nullable=False)

    def public(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "category": self.category,
            "unit_price": float(self.unit_price),
            "quantity": self.quantity,
            "line_total": float(self.line_total),
        }

class PaymentControl(db.Model):
    __tablename__ = "payment_controls"
    payment_id = db.Column(db.String(36), db.ForeignKey("payments.id"), primary_key=True)
    booking_claim = db.Column(db.String(36), unique=True)
    refunded = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0"))
    auto_hours = db.Column(db.Integer)
    terms_version = db.Column(db.String(100))
    settlement_id = db.Column(db.String(64))
    provider_hold = db.Column(db.Boolean, nullable=False, default=False)


class PaymentReceipt(db.Model):
    event = db.Column(db.String(64))
    reference = db.Column(db.String(120))
    received_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    __tablename__ = "payment_receipts"
    digest = db.Column(db.String(64), primary_key=True)


class PayoutRecipient(db.Model):
    __tablename__ = "payout_recipients"
    artisan_id = db.Column(db.String(36), db.ForeignKey("artisan_profiles.id"), primary_key=True)
    code = db.Column(db.String(100), nullable=False)
    last_four = db.Column(db.String(4), nullable=False)


class PaymentOperation(UUIDMixin, db.Model):
    __tablename__ = "payment_operations"
    payment_id = db.Column(db.String(36), db.ForeignKey("payments.id"))
    shop_order_id = db.Column(db.String(36), db.ForeignKey("shop_orders.id"), index=True)
    kind = db.Column(db.String(16), nullable=False)
    request_key = db.Column(db.String(100), unique=True, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    recipient = db.Column(db.String(100))
    provider_id = db.Column(db.String(100))
    status = db.Column(db.String(24), nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (db.UniqueConstraint("kind", "provider_id", name="uq_operation_provider_id"),
                      db.Index("ix_operation_payment", "payment_id"))

class JournalPosting(UUIDMixin, db.Model):
    __tablename__ = "journal_postings"
    reference = db.Column(db.String(120), nullable=False)
    event = db.Column(db.String(48), nullable=False)
    debit = db.Column(db.String(64), nullable=False)
    credit = db.Column(db.String(64), nullable=False)
    units = db.Column(db.BigInteger, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (db.UniqueConstraint("reference", "event", name="uq_journal_reference_event"),)

class PaymentJob(db.Model):
    cursor = db.Column(db.JSON)
    __tablename__ = "payment_jobs"
    key = db.Column(db.String(90), primary_key=True)
    kind = db.Column(db.String(24), nullable=False)
    record_id = db.Column(db.String(36), nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    due_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    state = db.Column(db.String(16), default="pending", nullable=False)
    last_error = db.Column(db.String(100))

class ProviderDispute(db.Model):
    __tablename__ = "provider_disputes"
    provider_id = db.Column(db.String(64), primary_key=True)
    reference = db.Column(db.String(120), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False)
    resolution = db.Column(db.String(64))
    deduction_units = db.Column(db.BigInteger, nullable=False, default=0)

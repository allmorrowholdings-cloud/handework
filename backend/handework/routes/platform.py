from datetime import datetime, timezone
from decimal import Decimal
from flask import Blueprint, jsonify, request
from flask_jwt_extended import decode_token, get_jwt_identity, jwt_required, verify_jwt_in_request
from flask_socketio import join_room
from ..extensions import db, socketio

from ..models import (ArtisanProfile, AuditLog, Booking, BookingStatus, Conversation, Course, Dispute, FileAsset, LedgerEntry, Message, Notification, Organization, OrganizationMember, PromoCode, PushDevice, Referral, Review, Role, Subscription, SupportTicket, TrainingProvider, Verification, WalletAccount)
from ..security import current_user, role_required
from ..services.storage import upload_file

bp = Blueprint("platform", __name__)


def conversation_for_user(conversation_id, user):
    row = Conversation.query.get_or_404(conversation_id)
    if user.role != Role.ADMIN and user.id not in (row.customer_id, row.artisan_user_id): return None
    return row


@bp.get("/conversations")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def conversations():
    user = current_user(); query = Conversation.query
    if user.role != Role.ADMIN: query = query.filter(db.or_(Conversation.customer_id == user.id, Conversation.artisan_user_id == user.id))
    rows = query.order_by(Conversation.last_message_at.desc(), Conversation.created_at.desc()).limit(100).all()
    items = []
    for row in rows:
        booking = Booking.query.get(row.booking_id); last = Message.query.filter_by(conversation_id=row.id).order_by(Message.created_at.desc()).first()
        items.append({"id": row.id, "booking_id": row.booking_id, "reference": booking.reference, "title": booking.service, "last_message": last.body if last else None, "last_message_at": row.last_message_at.isoformat() if row.last_message_at else None})
    return jsonify({"items": items})


@bp.route("/conversations/<conversation_id>/messages", methods=["GET", "POST"])
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def messages(conversation_id):
    user = current_user(); conversation = conversation_for_user(conversation_id, user)
    if not conversation: return jsonify({"message": "Conversation not found"}), 404
    if request.method == "GET":
        rows = Message.query.filter_by(conversation_id=conversation.id).filter(Message.deleted_at.is_(None)).order_by(Message.created_at.asc()).limit(300).all()
        return jsonify({"items": [{"id": row.id, "sender_id": row.sender_id, "body": row.body, "media_url": row.media_url, "media_type": row.media_type, "created_at": row.created_at.isoformat(), "edited_at": row.edited_at.isoformat() if row.edited_at else None} for row in rows]})
    data = request.get_json(silent=True) or {}; body = str(data.get("body") or "").strip(); media_url = data.get("media_url")
    if not body and not media_url: return jsonify({"message": "Message or attachment is required"}), 422
    row = Message(conversation_id=conversation.id, sender_id=user.id, body=body[:4000] or None, media_url=media_url, media_type=data.get("media_type")); db.session.add(row); db.session.flush(); conversation.last_message_at = row.created_at; db.session.commit()
    payload = {"id": row.id, "conversation_id": conversation.id, "sender_id": user.id, "body": row.body, "media_url": row.media_url, "media_type": row.media_type, "created_at": row.created_at.isoformat()}
    socketio.emit("message.created", payload, to=f"conversation:{conversation.id}")
    return jsonify(payload), 201


@bp.patch("/messages/<message_id>")
@role_required(Role.CUSTOMER, Role.ARTISAN)
def edit_message(message_id):
    row = Message.query.filter_by(id=message_id, sender_id=current_user().id, deleted_at=None).first_or_404(); body = str((request.get_json(silent=True) or {}).get("body") or "").strip()
    if not body: return jsonify({"message": "Message cannot be empty"}), 422
    row.body, row.edited_at = body[:4000], datetime.now(timezone.utc); db.session.commit(); return jsonify({"id": row.id, "body": row.body, "edited_at": row.edited_at.isoformat()})


@bp.get("/wallet")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def wallet():
    rows = WalletAccount.query.filter_by(user_id=current_user().id).all()
    return jsonify({"accounts": [{"currency": row.currency, "available_balance": float(row.available_balance), "held_balance": float(row.held_balance)} for row in rows]})


@bp.get("/wallet/transactions")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def transactions():
    account_ids = [row.id for row in WalletAccount.query.filter_by(user_id=current_user().id).all()]
    rows = LedgerEntry.query.filter(LedgerEntry.account_id.in_(account_ids)).order_by(LedgerEntry.created_at.desc()).limit(200).all() if account_ids else []
    return jsonify({"items": [{"id": row.id, "reference": row.external_reference, "event": row.event_type, "direction": row.direction, "bucket": row.bucket, "amount": float(row.amount), "currency": row.currency, "created_at": row.created_at.isoformat()} for row in rows]})


@bp.route("/notifications", methods=["GET", "PATCH"])
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def notifications():
    user = current_user()
    if request.method == "PATCH":
        ids = (request.get_json(silent=True) or {}).get("ids", []); Notification.query.filter(Notification.user_id == user.id, Notification.id.in_(ids)).update({Notification.read_at: datetime.now(timezone.utc)}, synchronize_session=False); db.session.commit()
    rows = Notification.query.filter_by(user_id=user.id, channel="in_app").order_by(Notification.created_at.desc()).limit(100).all()
    return jsonify({"items": [{"id": row.id, "title": row.title, "body": row.body, "data": row.data, "created_at": row.created_at.isoformat(), "read_at": row.read_at.isoformat() if row.read_at else None} for row in rows]})


@bp.post("/push-devices")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def register_push_device():
    data = request.get_json(silent=True) or {}; token = str(data.get("expo_push_token") or "")
    if not token.startswith("ExponentPushToken") and not token.startswith("ExpoPushToken"): return jsonify({"message": "Invalid Expo push token"}), 422
    row = PushDevice.query.filter_by(expo_push_token=token).first() or PushDevice(expo_push_token=token)
    row.user_id, row.platform, row.active = current_user().id, str(data.get("platform") or "unknown"), True; db.session.add(row); db.session.commit(); return jsonify({"id": row.id}), 201


@bp.post("/uploads")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def upload():
    user = current_user(); purpose = str(request.form.get("purpose") or "booking_media"); booking_id = request.form.get("booking_id")
    if booking_id:
        booking = Booking.query.get_or_404(booking_id); artisan_user = booking.artisan.user_id if booking.artisan else None
        if user.role != Role.ADMIN and user.id not in (booking.customer_id, artisan_user): return jsonify({"message": "Booking not found"}), 404
    try: url = upload_file(request.files.get("file"), user.id, purpose)
    except (ValueError, RuntimeError) as error: return jsonify({"message": str(error)}), 422
    asset = FileAsset(owner_id=user.id, booking_id=booking_id, purpose=purpose, url=url, mime_type=request.files["file"].mimetype); db.session.add(asset); db.session.commit(); return jsonify({"id": asset.id, "url": url, "scan_status": asset.scan_status}), 201


@bp.route("/disputes", methods=["GET", "POST"])
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def disputes():
    user = current_user()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}; booking = Booking.query.get_or_404(data.get("booking_id")); artisan_user = booking.artisan.user_id if booking.artisan else None
        if user.role != Role.ADMIN and user.id not in (booking.customer_id, artisan_user): return jsonify({"message": "Booking not found"}), 404
        if booking.status not in (BookingStatus.FUNDED, BookingStatus.EN_ROUTE, BookingStatus.IN_PROGRESS, BookingStatus.COMPLETION_SUBMITTED): return jsonify({"message": "This booking cannot be disputed from its current state"}), 409
        row = Dispute(booking_id=booking.id, opened_by_id=user.id, reason=str(data.get("reason") or "other"), description=str(data.get("description") or "").strip()); booking.status = BookingStatus.DISPUTED; db.session.add(row); db.session.commit(); return jsonify({"id": row.id, "status": row.status}), 201
    query = Dispute.query
    if user.role != Role.ADMIN:
        allowed_bookings = db.select(Booking.id).where(db.or_(Booking.customer_id == user.id, Booking.artisan_id.in_(db.select(ArtisanProfile.id).where(ArtisanProfile.user_id == user.id))))
        query = query.filter(Dispute.booking_id.in_(allowed_bookings))
    rows = query.order_by(Dispute.created_at.desc()).all(); return jsonify({"items": [{"id": row.id, "booking_id": row.booking_id, "reason": row.reason, "status": row.status, "created_at": row.created_at.isoformat()} for row in rows]})


@bp.post("/reviews")
@role_required(Role.CUSTOMER)
def review():
    data = request.get_json(silent=True) or {}; booking = Booking.query.filter_by(id=data.get("booking_id"), customer_id=current_user().id, status=BookingStatus.COMPLETED).first_or_404(); rating = int(data.get("rating") or 0)
    if not 1 <= rating <= 5: return jsonify({"message": "Rating must be from 1 to 5"}), 422
    if Review.query.filter_by(booking_id=booking.id).first(): return jsonify({"message": "This booking already has a review"}), 409
    row = Review(booking_id=booking.id, customer_id=current_user().id, artisan_id=booking.artisan_id, rating=rating, comment=str(data.get("comment") or "")[:3000]); db.session.add(row); db.session.flush()
    aggregate = db.session.query(db.func.avg(Review.rating), db.func.count(Review.id)).filter_by(artisan_id=booking.artisan_id, moderation_status="published").first(); artisan = ArtisanProfile.query.get(booking.artisan_id); artisan.rating_average, artisan.review_count = aggregate[0], aggregate[1]; db.session.commit(); return jsonify({"id": row.id}), 201


@bp.get("/referrals")
@role_required(Role.CUSTOMER, Role.ARTISAN)
def referrals():
    user = current_user(); rows = Referral.query.filter_by(referrer_id=user.id).order_by(Referral.created_at.desc()).all(); return jsonify({"code": user.referral_code, "items": [{"id": row.id, "status": row.status, "reward_amount": float(row.reward_amount)} for row in rows]})


@bp.post("/promo-codes/validate")
@role_required(Role.CUSTOMER)
def promo_validate():
    data = request.get_json(silent=True) or {}; code = str(data.get("code") or "").strip().upper(); now = datetime.now(timezone.utc); row = PromoCode.query.filter_by(code=code, active=True).first()
    if not row or (row.starts_at and row.starts_at > now) or (row.ends_at and row.ends_at < now) or (row.max_uses is not None and row.use_count >= row.max_uses): return jsonify({"message": "Promo code is not valid", "valid": False}), 422
    amount = Decimal(str(data.get("amount") or "0"))
    if row.minimum_amount and amount < row.minimum_amount: return jsonify({"message": f"Minimum amount is {row.currency} {row.minimum_amount}", "valid": False}), 422
    discount = row.discount_value if row.discount_type == "fixed" else (amount * row.discount_value / Decimal(100)).quantize(Decimal("0.01")); return jsonify({"valid": True, "discount": float(min(discount, amount)), "currency": row.currency})


@bp.post("/subscriptions")
@role_required(Role.ARTISAN)
def subscription():
    plan = str((request.get_json(silent=True) or {}).get("plan") or "pro-monthly")
    row = Subscription(user_id=current_user().id, plan=plan, status="pending"); db.session.add(row); db.session.commit(); return jsonify({"id": row.id, "status": row.status, "message": "Subscription price must be confirmed through the configured payment plan"}), 201


@bp.get("/training/courses")
def courses():
    rows = Course.query.filter_by(published=True).order_by(Course.created_at.desc()).limit(100).all(); items=[]
    providers = {provider.id: provider for provider in TrainingProvider.query.filter(TrainingProvider.id.in_({row.provider_id for row in rows})).all()} if rows else {}
    for row in rows:
        provider = providers.get(row.provider_id)
        if provider is None or provider.verification_status != "approved":
            continue
        items.append({"id": row.id, "title": row.title, "trade": row.trade, "city": row.city, "delivery_mode": row.delivery_mode, "fee": float(row.fee) if row.fee is not None else None, "currency": row.currency, "provider": provider.name, "enrollment_url": row.enrollment_url})
    return jsonify({"items":items})


@bp.route("/organizations", methods=["GET", "POST"])
@role_required(Role.CUSTOMER, Role.ADMIN)
def organizations():
    user=current_user()
    if request.method=="POST":
        data=request.get_json(silent=True) or {}; name=str(data.get("name") or "").strip(); email=str(data.get("billing_email") or user.email).strip()
        if not name:return jsonify({"message":"Organization name is required"}),422
        row=Organization(name=name,billing_email=email,country_code=str(data.get("country_code") or user.country_code));db.session.add(row);db.session.flush();db.session.add(OrganizationMember(organization_id=row.id,user_id=user.id,role="owner"));db.session.commit();return jsonify({"id":row.id,"status":row.status}),201
    memberships=OrganizationMember.query.filter_by(user_id=user.id).all();rows=Organization.query.filter(Organization.id.in_([x.organization_id for x in memberships])).all() if memberships else [];return jsonify({"items":[{"id":x.id,"name":x.name,"status":x.status} for x in rows]})


@bp.post("/support")
def support():
    verify_jwt_in_request(optional=True); user_id=get_jwt_identity();data=request.get_json(silent=True) or {};message=str(data.get("message") or "").strip();email=str(data.get("email") or "").strip()
    if user_id and not email: email=current_user().email
    if data.get("booking_id"):
        booking = db.session.get(Booking, data["booking_id"])
        if not booking or (user_id and user_id not in (booking.customer_id, booking.artisan.user_id if booking.artisan else None)):
            return jsonify({"message": "Booking could not be found"}), 404
    if not email or not message:return jsonify({"message":"Email and message are required"}),422
    priority="urgent" if str(data.get("topic") or "").lower()=="safety" else "normal";row=SupportTicket(user_id=user_id,booking_id=data.get("booking_id"),email=email,topic=str(data.get("topic") or "general"),message=message,priority=priority);db.session.add(row);db.session.commit();return jsonify({"id":row.id,"status":row.status}),201


@socketio.on("join.conversation")
def socket_join(data):
    try: user_id = decode_token(data.get("token", ""))["sub"]
    except Exception: return {"ok": False, "error": "unauthorized"}
    conversation = Conversation.query.get(data.get("conversation_id"))
    if not conversation or user_id not in (conversation.customer_id, conversation.artisan_user_id): return {"ok": False, "error": "forbidden"}
    join_room(f"conversation:{conversation.id}"); return {"ok": True}

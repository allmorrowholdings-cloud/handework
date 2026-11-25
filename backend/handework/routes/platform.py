from datetime import datetime, timezone
from decimal import Decimal
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import decode_token, get_jwt_identity, jwt_required, verify_jwt_in_request
from flask_socketio import join_room
from ..services.email_delivery import booking_email
from ..extensions import db, socketio

from ..models import (ArtisanProfile, AuditLog, Booking, BookingStatus, Conversation, Course, Dispute, FileAsset, LedgerEntry, Message, Notification, Organization, OrganizationMember, PortfolioItem, PromoCode, PushDevice, Referral, Review, Role, ShopProductMedia, Subscription, SupportTicket, TrainingProvider, Verification, WalletAccount, WorkProofEvidence)
from ..security import current_user, role_required
from ..services.storage import upload_file, private_download_url, metadata_for, delete_object

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
        return jsonify({"items": [{"id": row.id, "sender_id": row.sender_id, "body": row.body, "media_url": private_download_url(row.media_url), "media_type": row.media_type, "created_at": row.created_at.isoformat(), "edited_at": row.edited_at.isoformat() if row.edited_at else None} for row in rows]})
    data = request.get_json(silent=True) or {}; body = str(data.get("body") or "").strip(); media_url = data.get("media_url")
    if media_url:
        asset_id = str(media_url).removeprefix("asset:")
        asset = FileAsset.query.filter_by(id=asset_id, owner_id=user.id, purpose="chat_media", deleted_at=None).first()
        if not asset: return jsonify({"message":"Choose a file uploaded for this message."}), 422
        media_url = asset.url
    if not body and not media_url: return jsonify({"message": "Message or attachment is required"}), 422
    row = Message(conversation_id=conversation.id, sender_id=user.id, body=body[:4000] or None, media_url=media_url, media_type=data.get("media_type")); db.session.add(row); db.session.flush(); conversation.last_message_at = row.created_at; db.session.commit()
    payload = {"id": row.id, "conversation_id": conversation.id, "sender_id": user.id, "body": row.body, "media_url": private_download_url(row.media_url), "media_type": row.media_type, "created_at": row.created_at.isoformat()}
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
    from ..models import PaymentOperation, Payment
    transfers = (db.session.query(Payment.currency, db.func.sum(PaymentOperation.amount))
                 .join(PaymentOperation, PaymentOperation.payment_id == Payment.id)
                 .join(ArtisanProfile, ArtisanProfile.id == Payment.artisan_id)
                 .filter(ArtisanProfile.user_id == current_user().id, PaymentOperation.kind == "payout",
                         PaymentOperation.status == "success").group_by(Payment.currency).all())
    paid = dict(transfers)
    return jsonify({"accounts": [{"transferred": float(paid.get(row.currency, 0)), "currency": row.currency, "available_balance": float(row.available_balance), "held_balance": float(row.held_balance)} for row in rows]})


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
        ids = (request.get_json(silent=True) or {}).get("ids", []); Notification.query.filter(Notification.user_id == user.id, Notification.channel == 'in_app', Notification.id.in_(ids)).update({Notification.read_at: datetime.now(timezone.utc)}, synchronize_session=False); db.session.commit()
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
    if purpose not in {"booking_media", "chat_media", "completion_evidence", "dispute_evidence", "workproof_evidence", "profile_picture"}: return jsonify({"message": "Unsupported attachment type"}), 422
    if purpose in {"booking_media","completion_evidence","dispute_evidence"} and not booking_id: return jsonify({"message": "Select a booking for this file"}), 422
    if purpose in {"workproof_evidence","profile_picture"} and user.role not in (Role.ARTISAN, Role.ADMIN): return jsonify({"message":"Artisan account required"}), 403
    if booking_id:
        booking = Booking.query.get_or_404(booking_id); artisan_user = booking.artisan.user_id if booking.artisan else None
        if user.role != Role.ADMIN and user.id not in (booking.customer_id, artisan_user): return jsonify({"message": "Booking not found"}), 404
        if purpose == "completion_evidence" and (user.id != artisan_user or booking.status != BookingStatus.IN_PROGRESS):
            return jsonify(message="Only the assigned artisan may submit completion evidence during work"), 403
        if purpose == "dispute_evidence" and not Dispute.query.filter_by(booking_id=booking.id, status="open").first(): return jsonify({"message":"Open a dispute before attaching dispute evidence"}), 409
    file = request.files.get("file")
    replaced_avatar = None
    try:
        stored = upload_file(file, user.id, purpose, private=True)
        asset = FileAsset(owner_id=user.id, booking_id=booking_id, purpose=purpose, **metadata_for(stored)); db.session.add(asset); db.session.flush()
        if purpose == "profile_picture":
            profile=ArtisanProfile.query.filter_by(user_id=user.id).first_or_404();replaced_avatar=db.session.get(FileAsset,profile.avatar_file_id) if profile.avatar_file_id else None
            profile.avatar_file_id=asset.id; profile.avatar_url=asset.url
            if replaced_avatar:
                asset.replaces_asset_id = replaced_avatar.id
                replaced_avatar.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
    except ValueError as error:
        db.session.rollback(); return jsonify({"message": str(error)}), 422
    except RuntimeError as error:
        db.session.rollback()
        if "stored" in locals():
            try: delete_object(stored.url)
            except Exception: current_app.logger.exception("Failed upload cleanup failed")
        return jsonify({"message": str(error)}), 503
    except Exception:
        db.session.rollback()
        if "stored" in locals():
            try: delete_object(stored.url)
            except Exception: current_app.logger.exception("Orphan storage object cleanup failed")
        raise
    if replaced_avatar:
        try: delete_object(replaced_avatar.url)
        except Exception: current_app.logger.exception("Replaced profile image cleanup failed")
    return jsonify({"id": asset.id, "url": "asset:" + asset.id if purpose == "chat_media" else private_download_url(asset.url), "scan_status": asset.scan_status}), 201


def _locked_evidence(asset, user):
    if user.role == Role.ADMIN or asset.purpose not in {"completion_evidence", "dispute_evidence"}:
        return False
    booking = db.session.get(Booking, asset.booking_id)
    return booking and booking.status in {
        BookingStatus.COMPLETION_SUBMITTED, BookingStatus.DISPUTED,
        BookingStatus.COMPLETED, BookingStatus.REFUNDED,
    }


def _asset_accessible(asset, user):
    if user.role == Role.ADMIN or asset.owner_id == user.id:
        return True
    if asset.booking_id:
        booking = Booking.query.get(asset.booking_id)
        return bool(booking and user.id in (booking.customer_id, booking.artisan.user_id if booking.artisan else None))
    return False


@bp.get("/files/<asset_id>/download")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def download_file(asset_id):
    asset = FileAsset.query.filter_by(id=asset_id).first_or_404(); user=current_user()
    if asset.deleted_at or not _asset_accessible(asset,user): return jsonify({"message":"File not found"}),404
    return jsonify({"url":private_download_url(asset.url,300),"expires_in":300,"mime_type":asset.mime_type,"filename":asset.original_filename}),200


@bp.put("/files/<asset_id>")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def replace_file(asset_id):
    old=FileAsset.query.filter_by(id=asset_id).with_for_update().first_or_404();user=current_user()
    if old.deleted_at or (user.role!=Role.ADMIN and old.owner_id!=user.id): return jsonify({"message":"File not found"}),404
    if _locked_evidence(old, user):
        return jsonify(message="Submitted evidence cannot be replaced"), 409
    verification=Verification.query.filter_by(file_asset_id=old.id).first()
    if verification and verification.status=="approved" and user.role!=Role.ADMIN: return jsonify({"message":"Approved verification replacement requires administrator review"}),409
    try:
        stored=upload_file(request.files.get("file"),old.owner_id,old.purpose,private=True)
        replacement=FileAsset(owner_id=old.owner_id,booking_id=old.booking_id,purpose=old.purpose,replaces_asset_id=old.id,**metadata_for(stored));db.session.add(replacement);db.session.flush()
        for row in PortfolioItem.query.filter_by(file_asset_id=old.id): row.file_asset_id=replacement.id;row.media_url=replacement.url;row.moderation_status="pending";row.media_type="video" if replacement.mime_type.startswith("video/") else "image"
        for row in Verification.query.filter_by(file_asset_id=old.id): row.file_asset_id=replacement.id;row.file_url=replacement.url;row.status="pending";row.reviewer_id=None;row.decided_at=None
        for row in WorkProofEvidence.query.filter_by(file_asset_id=old.id): row.file_asset_id=replacement.id;row.status="pending";row.reviewer_id=None;row.decided_at=None
        for row in ArtisanProfile.query.filter_by(avatar_file_id=old.id): row.avatar_file_id=replacement.id;row.avatar_url=replacement.url
        for row in ShopProductMedia.query.filter_by(file_asset_id=old.id): row.file_asset_id=replacement.id
        if old.purpose == "chat_media":
            Message.query.filter_by(media_url=old.url).update({"media_url": replacement.url, "media_type": replacement.mime_type})
        old.deleted_at=datetime.now(timezone.utc);db.session.add(AuditLog(actor_id=user.id,action="file.replaced",entity_type="file_asset",entity_id=old.id,before={"sha256":old.sha256},after={"asset_id":replacement.id,"sha256":replacement.sha256}));db.session.commit()
    except ValueError as error:
        db.session.rollback();return jsonify({"message":str(error)}),422
    except RuntimeError as error:
        db.session.rollback()
        if "stored" in locals():
            try: delete_object(stored.url)
            except Exception: current_app.logger.exception("Failed replacement cleanup failed")
        return jsonify({"message":str(error)}),503
    except Exception:
        db.session.rollback()
        if "stored" in locals():
            try: delete_object(stored.url)
            except Exception: current_app.logger.exception("Orphan storage object cleanup failed")
        raise
    try: delete_object(old.url)
    except Exception: current_app.logger.exception("Replaced object cleanup failed for asset %s",old.id)
    return jsonify({"id":replacement.id,"url":private_download_url(replacement.url,300),"expires_in":300}),200


@bp.delete("/files/<asset_id>")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def remove_file(asset_id):
    asset=FileAsset.query.filter_by(id=asset_id).with_for_update().first_or_404();user=current_user()
    if asset.deleted_at or (user.role!=Role.ADMIN and asset.owner_id!=user.id): return jsonify({"message":"File not found"}),404
    if _locked_evidence(asset, user):
        return jsonify(message="Submitted evidence cannot be removed"), 409
    verification=Verification.query.filter_by(file_asset_id=asset.id).first()
    if verification and verification.status=="approved" and user.role!=Role.ADMIN: return jsonify({"message":"Approved verification documents require administrator approval to remove"}),409
    for row in Verification.query.filter_by(file_asset_id=asset.id): row.file_asset_id=None;row.file_url=None;row.status="replacement_required"
    for row in PortfolioItem.query.filter_by(file_asset_id=asset.id).all(): db.session.delete(row)
    for row in WorkProofEvidence.query.filter_by(file_asset_id=asset.id): row.file_asset_id=None;row.status="rejected";row.decision_reason="Evidence file removed"
    for row in ArtisanProfile.query.filter_by(avatar_file_id=asset.id): row.avatar_file_id=None;row.avatar_url=None
    ShopProductMedia.query.filter_by(file_asset_id=asset.id).delete(synchronize_session=False)
    if asset.purpose == "chat_media":
        Message.query.filter_by(media_url=asset.url).update({"media_url": None, "media_type": None})
    asset.deleted_at=datetime.now(timezone.utc);db.session.add(AuditLog(actor_id=user.id,action="file.deleted",entity_type="file_asset",entity_id=asset.id,before={"purpose":asset.purpose,"sha256":asset.sha256},after={"deleted":True}));db.session.commit()
    try: delete_object(asset.url)
    except Exception: current_app.logger.exception("Deleted object cleanup failed for asset %s",asset.id)
    return jsonify({"id":asset.id,"deleted":True}),200


@bp.route("/disputes", methods=["GET", "POST"])
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def disputes():
    user = current_user()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}; booking = Booking.query.filter_by(id=data.get("booking_id")).with_for_update().first_or_404(); artisan_user = booking.artisan.user_id if booking.artisan else None
        if user.role != Role.ADMIN and user.id not in (booking.customer_id, artisan_user): return jsonify({"message": "Booking not found"}), 404
        if booking.status not in (BookingStatus.FUNDED, BookingStatus.EN_ROUTE, BookingStatus.IN_PROGRESS, BookingStatus.COMPLETION_SUBMITTED): return jsonify({"message": "This booking cannot be disputed from its current state"}), 409
        row = Dispute(booking_id=booking.id, opened_by_id=user.id, reason=str(data.get("reason") or "other"), description=str(data.get("description") or "").strip()); booking.status = BookingStatus.DISPUTED; db.session.add(row)
        booking_email(booking, "Dispute opened", f"A dispute has been opened for {booking.reference}.")
        db.session.commit(); return jsonify({"id": row.id, "status": row.status}), 201
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
    try:
        from ..security import session_inactive
        claims = decode_token(data.get("token", ""))
        if claims.get("type") != "access" or session_inactive({}, claims):
            return {"ok": False, "error": "Sign in again"}
        user_id = claims["sub"]
    except Exception: return {"ok": False, "error": "unauthorized"}
    conversation = Conversation.query.get(data.get("conversation_id"))
    if not conversation or user_id not in (conversation.customer_id, conversation.artisan_user_id): return {"ok": False, "error": "forbidden"}
    join_room(f"conversation:{conversation.id}"); return {"ok": True}

@bp.post("/disputes/<dispute_id>/responses")
@role_required(Role.ARTISAN, Role.CUSTOMER)
def dispute_response(dispute_id):
    from ..models import AuditLog
    dispute = Dispute.query.filter_by(id=dispute_id,status="open").with_for_update().first_or_404()
    booking = db.get_or_404(Booking,dispute.booking_id)
    actor = current_user()
    if actor.id not in {booking.customer_id,booking.artisan.user_id if booking.artisan else None}:
        return jsonify(message="Dispute unavailable"),404
    data=request.get_json(silent=True) or {}
    message=str(data.get("message") or "").strip()
    if not 1<=len(message)<=4000: return jsonify(message="Enter a response of up to 4,000 characters"),422
    asset_id=data.get("asset_id")
    if asset_id and not FileAsset.query.filter_by(id=asset_id,owner_id=actor.id,booking_id=booking.id,purpose="dispute_evidence",deleted_at=None).first():
        return jsonify(message="Evidence must belong to this booking"),422
    db.session.add(AuditLog(actor_id=actor.id,action="dispute.response",entity_type="dispute",entity_id=dispute.id,
                            after={"message":message,"asset_id":asset_id}))
    booking_email(booking, "Dispute response", f"A new response is available for {booking.reference}.", exclude=actor.id)
    db.session.commit()
    return jsonify(status="recorded"),201

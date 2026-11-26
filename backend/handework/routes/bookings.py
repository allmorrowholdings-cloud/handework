import os
import secrets
from uuid import UUID, uuid5
from sqlalchemy.exc import IntegrityError
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, time, timezone
import re
from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models import ArtisanProfile, Availability, FileAsset, Booking, BookingStatus, BookingStatusEvent, Conversation, JobChange, Quote, Role
from ..security import current_user, role_required
from ..services.commission import commission_bps
from ..services.payment_plan import installments, validate_schedule
from ..services.storage import private_download_url
from ..services.notifications import dispatch_notifications, queue_notifications

bp = Blueprint("bookings", __name__)

ALLOWED_TRANSITIONS = {
    BookingStatus.REQUESTED: {BookingStatus.QUOTED, BookingStatus.CANCELLED},
    BookingStatus.QUOTED: {BookingStatus.ACCEPTED, BookingStatus.CANCELLED},
    BookingStatus.ACCEPTED: {BookingStatus.FUNDED, BookingStatus.CANCELLED},
    BookingStatus.FUNDED: {BookingStatus.EN_ROUTE, BookingStatus.DISPUTED, BookingStatus.REFUNDED},
    BookingStatus.EN_ROUTE: {BookingStatus.IN_PROGRESS, BookingStatus.DISPUTED, BookingStatus.CANCELLED},
    BookingStatus.IN_PROGRESS: {BookingStatus.COMPLETION_SUBMITTED, BookingStatus.DISPUTED},
    BookingStatus.COMPLETION_SUBMITTED: {BookingStatus.COMPLETED, BookingStatus.DISPUTED},
    BookingStatus.DISPUTED: {BookingStatus.COMPLETED, BookingStatus.REFUNDED},
}


def transition(booking, target, actor, note=None):
    target = BookingStatus(target)
    if target not in ALLOWED_TRANSITIONS.get(booking.status, set()): raise ValueError(f"Cannot move booking from {booking.status.value} to {target.value}")
    before = booking.status.value; booking.status = target
    if target == BookingStatus.COMPLETED: booking.completed_at = datetime.now(timezone.utc)
    db.session.add(BookingStatusEvent(booking_id=booking.id, actor_id=actor.id, from_status=before, to_status=target.value, note=note))


def booking_for_user(booking_id, user):
    booking = db.get_or_404(Booking, booking_id)
    artisan_user_id = booking.artisan.user_id if booking.artisan else None
    if user.role != Role.ADMIN and user.id not in (booking.customer_id, artisan_user_id): return None
    return booking


@bp.route("/bookings", methods=["GET", "POST"])
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def bookings():
    user = current_user()
    if request.method == "GET":
        query = Booking.query
        if user.role == Role.CUSTOMER: query = query.filter_by(customer_id=user.id)
        elif user.role == Role.ARTISAN:
            profile = ArtisanProfile.query.filter_by(user_id=user.id).first_or_404(); query = query.filter_by(artisan_id=profile.id)
        rows = query.order_by(Booking.created_at.desc()).limit(100).all()
        return jsonify({"items": [row.public() for row in rows]})
    if user.role != Role.CUSTOMER: return jsonify({"message": "Only customers can create bookings"}), 403
    data = request.get_json(silent=True) or {}
    booking_id = None
    request_key = request.headers.get("Idempotency-Key")
    if request_key:
        try:
            booking_id = str(uuid5(UUID(user.id), str(UUID(request_key))))
        except ValueError:
            return jsonify({"message": "Invalid booking request key"}), 422
        existing = db.session.get(Booking, booking_id)
        if existing:
            return jsonify(existing.public())
    required = ("service", "description", "address", "area", "city", "contact_phone")
    if any(not str(data.get(field) or "").strip() for field in required): return jsonify({"message": "Complete the service, job, address, city and contact fields", "code": "missing_booking_fields"}), 422
    scheduled = None
    if data.get("scheduled_date"):
        try:
            hour = {"morning": 8, "midday": 12, "evening": 16}.get(data.get("time_window", "morning"), 8)
            minute = 0
            if data.get("start_time") is not None:
                value = str(data["start_time"])
                if not re.fullmatch(r"(?:0[6-9]|1[0-9]|20):(?:00|30)", value) or value.startswith("20:") and value != "20:00":
                    return jsonify(message="Start time must be from 6:00 AM to 8:00 PM in 30-minute intervals"), 422
                hour, minute = map(int, value.split(":"))
            selected_date = date.fromisoformat(data["scheduled_date"])
            if selected_date < datetime.now(timezone.utc).date():
                return jsonify({
                    "message": "Choose today or a future date for your job.",
                    "code": "past_booking_date"
                }), 422
            scheduled = datetime.combine(selected_date, time(hour, minute), tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return jsonify({"message": "Choose a valid job date."}), 422
    booking = Booking(reference=f"VV-{secrets.token_hex(4).upper()}", customer_id=user.id, service=data["service"].strip(), description=data["description"].strip(), address=data["address"].strip(), area=data["area"].strip(), city=data["city"].strip(), scheduled_start=scheduled, budget_type=data.get("budget_type", "quote"), budget_amount=data.get("budget") or None, contact_phone=data["contact_phone"].strip())
    instant_artisan = None
    if data.get("coordinates"):
        from .marketplace import parse_coordinates
        coords=parse_coordinates(data["coordinates"])
        if coords is None:
            return jsonify(message="Invalid booking location"),422
        booking.latitude,booking.longitude=coords
    if data.get("smart_dispatch") is True:
        from .marketplace import ranked_artisans
        if booking.latitude is None:
            return jsonify(message="Select a job pin for Smart Dispatch"),422
        matches = ranked_artisans(booking.service if booking.service!="Help me choose" else booking.description,
                                  (booking.latitude,booking.longitude),100,weekday=scheduled.weekday() if scheduled else None)
        if not matches:
            return jsonify(message="No eligible artisan within service radius"),409
        data["artisan_id"]=matches[0]["id"]
    if data.get("artisan_id"):
        artisan = ArtisanProfile.query.filter_by(id=data["artisan_id"], verification_status="approved", available=True).first()
        if not artisan: return jsonify({"message": "This artisan is not available for booking"}), 409
        if booking.latitude is not None and artisan.latitude is not None and artisan.longitude is not None:
            from ..services.distance import haversine_km
            if haversine_km(booking.latitude,booking.longitude,artisan.latitude,artisan.longitude)>artisan.radius_km:
                return jsonify(message="The job is outside this artisan's service radius"),409
        booking.artisan_id = artisan.id
        if bool(data.get("instant_booking")):
            if not scheduled: return jsonify({"message": "Choose a date for instant booking"}), 422
            slot = Availability.query.filter_by(artisan_id=artisan.id, weekday=scheduled.weekday(), active=True).first()
            if not artisan.instant_booking or artisan.starting_price is None or not slot: return jsonify({"message": "Instant booking is not available for this artisan and date"}), 409
            booking.status, booking.agreed_amount, instant_artisan = BookingStatus.ACCEPTED, artisan.starting_price, artisan
    if booking_id:
        booking.id = booking_id
    db.session.add(booking)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        existing = db.session.get(Booking, booking_id) if booking_id else None
        if existing:
            return jsonify(existing.public())
        raise
    db.session.add(BookingStatusEvent(booking_id=booking.id, actor_id=user.id, to_status=booking.status.value, note="Instant booking accepted" if instant_artisan else "Booking requested"));notification_ids=queue_notifications(user,"Booking created",f"{booking.reference}: {booking.service} is {booking.status.value}.",{"booking_id":booking.id});
    if instant_artisan:
        db.session.add(Conversation(booking_id=booking.id,customer_id=user.id,artisan_user_id=instant_artisan.user_id));notification_ids.extend(queue_notifications(instant_artisan.user,"Instant booking received",f"{booking.reference} is scheduled for {scheduled.date().isoformat()} at {booking.currency} {float(booking.agreed_amount):.2f}.",{"booking_id":booking.id},urgent=True))
    elif booking.artisan_id:
        notification_ids.extend(queue_notifications(
            artisan.user, "Quotation requested",
            f"A customer requested a quotation for {booking.service}.",
            {"booking_id": booking.id},
        ))
    db.session.commit();dispatch_notifications(notification_ids)
    return jsonify(booking.public()), 201


@bp.get("/bookings/<booking_id>")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def booking_detail(booking_id):
    booking = booking_for_user(booking_id, current_user())
    if not booking: return jsonify({"message": "Booking not found"}), 404
    events = BookingStatusEvent.query.filter_by(booking_id=booking.id).order_by(BookingStatusEvent.occurred_at).all()
    quotes = Quote.query.filter_by(booking_id=booking.id).order_by(Quote.created_at.desc()).all()
    artisans = {profile.id: profile for profile in ArtisanProfile.query.filter(ArtisanProfile.id.in_({row.artisan_id for row in quotes})).all()} if quotes else {}
    conversation = Conversation.query.filter_by(booking_id=booking.id).first()
    changes = JobChange.query.filter_by(booking_id=booking.id).order_by(JobChange.created_at.desc()).all()
    files = FileAsset.query.filter_by(booking_id=booking.id, deleted_at=None).filter(FileAsset.purpose.in_(["booking_media","completion_evidence"])).all()
    from ..models import Dispute
    dispute=Dispute.query.filter_by(booking_id=booking.id,status="open").first()
    return jsonify({"open_dispute_id":dispute.id if dispute else None,"commission_bps":commission_bps(booking.service), "auto_terms":os.getenv("PAYMENT_AUTO_RELEASE_TERMS_VERSION") if os.getenv("PAYMENT_AUTO_RELEASE_ENABLED","").lower()=="true" else None, "auto_hours":int(os.getenv("PAYMENT_AUTO_RELEASE_HOURS","48")), "installments": installments(booking), "attachments": [{"id": file.id, "url": private_download_url(file.url), "mime_type": file.mime_type} for file in files], "booking": booking.public(), "changes": [row.public() for row in changes], "conversation_id": conversation.id if conversation else None, "events": [{"from": row.from_status, "to": row.to_status, "note": row.note, "occurred_at": row.occurred_at.isoformat()} for row in events], "quotes": [{"id": row.id, "artisan_id": row.artisan_id, "artisan_name": artisans[row.artisan_id].display_name, "amount": float(row.amount), "payment_schedule": row.payment_schedule, "currency": row.currency, "note": row.note, "status": row.status, "valid_until": row.valid_until.isoformat() if row.valid_until else None} for row in quotes]})


@bp.post("/bookings/<booking_id>/changes")
@role_required(Role.ARTISAN)
def propose_change(booking_id):
    booking = Booking.query.filter_by(id=booking_id).with_for_update(of=Booking).first_or_404()
    if not booking.artisan or booking.artisan.user_id != current_user().id:
        return jsonify({"message": "Booking not found"}), 404
    if booking.status != BookingStatus.IN_PROGRESS or booking.agreed_amount is None:
        return jsonify({"message": "Changes can only be proposed while work is in progress."}), 409
    changes = JobChange.query.filter_by(booking_id=booking.id).all()
    if any(change.status == "pending" for change in changes):
        return jsonify({"message": "Wait for the customer to respond to the existing change."}), 409
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "Enter a description and extra cost."}), 422
    description = data.get("description")
    try:
        amount = Decimal(str(data.get("extra_amount")))
        if not amount.is_finite() or not 0 < amount <= Decimal("9999999999.99") or amount != amount.quantize(Decimal("0.01")):
            raise InvalidOperation
    except InvalidOperation:
        return jsonify({"message": "Enter a positive extra cost with at most two decimal places."}), 422
    if not isinstance(description, str) or not 1 <= len(description.strip()) <= 500:
        return jsonify({"message": "Describe the change in 1 to 500 characters."}), 422
    current_total = booking.agreed_amount + sum(change.extra_amount for change in changes if change.status == "approved")
    if current_total + amount > Decimal("9999999999.99"):
        return jsonify({"message": "The new total exceeds the supported amount."}), 422
    change = JobChange(booking_id=booking.id, description=description.strip(), extra_amount=amount,
                       base_amount=current_total)
    db.session.add(change)
    db.session.commit()
    return jsonify(change.public()), 201


@bp.post("/bookings/<booking_id>/changes/<change_id>/decision")
@role_required(Role.CUSTOMER)
def decide_change(booking_id, change_id):
    booking = Booking.query.filter_by(id=booking_id, customer_id=current_user().id).with_for_update(of=Booking).first_or_404()
    if booking.status != BookingStatus.IN_PROGRESS:
        return jsonify({"message": "This job is no longer accepting changes."}), 409
    data = request.get_json(silent=True)
    decision = data.get("decision") if isinstance(data, dict) else None
    if decision not in ("approved", "declined"):
        return jsonify({"message": "Choose approve or decline."}), 422
    updated = JobChange.query.filter_by(id=change_id, booking_id=booking.id, status="pending").update({"status": decision})
    if not updated:
        return jsonify({"message": "This change is no longer awaiting a decision."}), 409
    db.session.commit()
    return jsonify({"status": decision})


@bp.post("/bookings/<booking_id>/quotes")
@role_required(Role.ARTISAN)
def quote(booking_id):
    user = current_user(); profile = ArtisanProfile.query.filter_by(user_id=user.id).first_or_404(); booking = Booking.query.get_or_404(booking_id)
    if profile.verification_status != "approved": return jsonify({"message": "Complete verification before quoting for work."}), 403
    if booking.artisan_id not in (None, profile.id): return jsonify({"message": "This request is assigned to another artisan"}), 409
    if booking.status not in (BookingStatus.REQUESTED, BookingStatus.QUOTED): return jsonify({"message": "This booking no longer accepts quotes"}), 409
    data = request.get_json(silent=True) or {}
    try:
        amount = Decimal(str(data.get("amount", "")))
        if not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999.99") or amount != amount.quantize(Decimal("0.01")):
            raise ValueError
    except (ValueError, InvalidOperation):
        return jsonify({"message": "Enter a positive quote with at most two decimal places."}), 422
    try:
        schedule = validate_schedule(data.get("payment_schedule"), amount)
    except ValueError:
        return jsonify(message="Installments must have labels and positive amounts totaling the quote"), 422
    row = Quote(payment_schedule=schedule, booking_id=booking.id, artisan_id=profile.id, amount=amount, note=str(data.get("note") or "")); db.session.add(row)
    db.session.flush()
    if booking.status == BookingStatus.REQUESTED: transition(booking, BookingStatus.QUOTED, user, "Quote submitted")
    notification_ids=queue_notifications(booking.customer,"New artisan quote",f"{profile.display_name} quoted {row.currency} {amount:.2f} for {booking.service}.",{"booking_id":booking.id,"quote_id":row.id});db.session.commit();dispatch_notifications(notification_ids);return jsonify({"id": row.id, "status": row.status, "amount": float(amount)}), 201


@bp.post("/bookings/<booking_id>/quotes/<quote_id>/accept")
@role_required(Role.CUSTOMER)
def accept_quote(booking_id, quote_id):
    user = current_user(); booking = Booking.query.filter_by(id=booking_id, customer_id=user.id).with_for_update().first_or_404(); row = Quote.query.filter_by(id=quote_id, booking_id=booking.id, status="submitted").first_or_404()
    if booking.status != BookingStatus.QUOTED: return jsonify({"message": "This quote can no longer be accepted"}), 409
    artisan = ArtisanProfile.query.filter_by(id=row.artisan_id).with_for_update().one()
    if artisan.verification_status != "approved":
        return jsonify({"message": "This professional is no longer eligible to accept this job."}), 409
    booking.artisan_id, booking.agreed_amount, row.status = row.artisan_id, row.amount, "accepted"
    Quote.query.filter(Quote.booking_id == booking.id, Quote.id != row.id).update({Quote.status: "declined"})
    transition(booking, BookingStatus.ACCEPTED, user, "Customer accepted quote")
    db.session.add(Conversation(booking_id=booking.id, customer_id=user.id, artisan_user_id=artisan.user_id));notification_ids=queue_notifications(artisan.user,"Quote accepted",f"Your {row.currency} {float(row.amount):.2f} quote for {booking.service} was accepted.",{"booking_id":booking.id},urgent=True);db.session.commit();dispatch_notifications(notification_ids)
    return jsonify({"booking": booking.public()})


@bp.post("/bookings/<booking_id>/status")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def update_status(booking_id):
    user = current_user(); Booking.query.filter_by(id=booking_id).with_for_update().first_or_404()
    booking = booking_for_user(booking_id, user)
    if not booking: return jsonify({"message": "Booking not found"}), 404
    data = request.get_json(silent=True) or {}
    target = str(data.get("status") or "")
    allowed_for_role = {
        Role.CUSTOMER: {BookingStatus.CANCELLED.value},
        Role.ARTISAN: {BookingStatus.EN_ROUTE.value, BookingStatus.IN_PROGRESS.value, BookingStatus.COMPLETION_SUBMITTED.value, BookingStatus.CANCELLED.value},
        Role.ADMIN: {BookingStatus.EN_ROUTE.value, BookingStatus.IN_PROGRESS.value, BookingStatus.COMPLETION_SUBMITTED.value, BookingStatus.CANCELLED.value},
    }
    if target not in allowed_for_role[user.role]: return jsonify({"message": "Use the dedicated payment, dispute or approval action for this status", "code": "role_transition_forbidden"}), 403
    try: transition(booking, data.get("status"), user, str(data.get("note") or "")[:500])
    except (ValueError, KeyError) as error: return jsonify({"message": str(error), "code": "invalid_transition"}), 409
    if target == BookingStatus.COMPLETION_SUBMITTED.value:
        from ..services.payment_jobs import enqueue
        enqueue("auto_release", booking.id)
    recipient=booking.customer if user.role==Role.ARTISAN else booking.artisan.user if booking.artisan else None;notification_ids=queue_notifications(recipient,"Booking updated",f"{booking.reference} is now {booking.status.value.replace('_',' ')}.",{"booking_id":booking.id},urgent=booking.status in (BookingStatus.EN_ROUTE,BookingStatus.COMPLETION_SUBMITTED)) if recipient else [];db.session.commit();dispatch_notifications(notification_ids);return jsonify({"booking": booking.public()})

@bp.get("/bookings/<booking_id>/route")
@role_required(Role.CUSTOMER,Role.ARTISAN,Role.ADMIN)
def job_route(booking_id):
    from ..services.maps import driving_route, LocationUnavailable
    booking=booking_for_user(booking_id,current_user())
    if not booking:
        return jsonify(message="Booking unavailable"),404
    artisan=booking.artisan
    if not artisan or None in (artisan.latitude,artisan.longitude,booking.latitude,booking.longitude):
        return jsonify(message="A route needs both a service location and a job pin"),409
    try:
        route=driving_route((artisan.latitude,artisan.longitude),(booking.latitude,booking.longitude))
    except LocationUnavailable as exc:
        return jsonify(message=str(exc)),503
    if not route:
        return jsonify(message="No driving route found"),404
    return jsonify(route)

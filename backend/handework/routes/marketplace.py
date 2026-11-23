from datetime import date
from math import isfinite
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models import ArtisanProfile, Availability, PortfolioItem, Role, Verification
from ..security import current_user, role_required
from ..services.distance import haversine_km
from ..services.maps import geocode
from ..services.matching import matching_score
from ..services.storage import upload_file
from ..services.workproof import public_workproof

bp = Blueprint("marketplace", __name__)


def parse_coordinates(value):
    try:
        latitude, longitude = [float(part.strip()) for part in value.split(",", 1)]
        if -90 <= latitude <= 90 and -180 <= longitude <= 180: return latitude, longitude
    except (ValueError, AttributeError): pass
    return None


@bp.get("/artisans/search")
def search_artisans():
    service = str(request.args.get("service") or "").strip()
    coordinates = parse_coordinates(request.args.get("coordinates", ""))
    if not coordinates and request.args.get("location"):
        coordinates = geocode(request.args["location"])
    try:
        requested_distance = float(request.args.get("distance_km", 25))
    except (TypeError, ValueError):
        return jsonify({"message": "Distance must be a number"}), 422
    if not isfinite(requested_distance):
        return jsonify({"message": "Distance must be a finite number"}), 422
    distance_limit = min(max(requested_distance, 1), 100)
    query = ArtisanProfile.query.filter_by(verification_status="approved", available=True)
    if service: query = query.filter(db.or_(ArtisanProfile.trade.ilike(f"%{service}%"), ArtisanProfile.secondary_services.ilike(f"%{service}%")))
    rows = []
    for profile in query.limit(250).all():
        if request.args.get("date"):
            try: requested_weekday = date.fromisoformat(request.args["date"]).weekday()
            except ValueError: return jsonify({"message": "Date must use YYYY-MM-DD"}), 422
            if not Availability.query.filter_by(artisan_id=profile.id, weekday=requested_weekday, active=True).first(): continue
        if coordinates and profile.latitude is not None and profile.longitude is not None:
            distance = haversine_km(coordinates[0], coordinates[1], profile.latitude, profile.longitude)
        elif coordinates:
            continue
        else:
            distance = 0.0
        if distance > min(distance_limit, profile.radius_km): continue
        card = profile.search_card(distance)
        card["match_score"] = matching_score(text_match=1 if service else .5, distance_km=distance, radius_km=profile.radius_km, rating=profile.rating_average, completion_rate=profile.completion_rate, available=profile.available, response_minutes=profile.response_minutes)
        rows.append(card)
    rows.sort(key=lambda item: (-item["match_score"], item["distance_km"]))
    return jsonify({"items": rows[:50], "meta": {"service": service, "coordinates_used": bool(coordinates), "distance_km": distance_limit}})


@bp.get("/artisans/<artisan_id>")
def artisan_detail(artisan_id):
    profile = ArtisanProfile.query.filter_by(id=artisan_id, verification_status="approved").first_or_404()
    portfolio = PortfolioItem.query.filter_by(artisan_id=profile.id, moderation_status="approved").order_by(PortfolioItem.created_at.desc()).all()
    return jsonify({"artisan": {**profile.search_card(0), "bio": profile.bio, "years_experience": profile.years_experience, "city": profile.city, "area": profile.area, "languages": profile.languages, "radius_km": profile.radius_km}, "workproof": public_workproof(profile), "portfolio": [{"id": item.id, "title": item.title, "description": item.description, "service": item.service, "media_url": item.media_url, "media_type": item.media_type, "before_after": item.before_after} for item in portfolio]})


@bp.route("/artisans/me", methods=["GET", "PATCH"])
@role_required(Role.ARTISAN)
def my_artisan_profile():
    profile = ArtisanProfile.query.filter_by(user_id=current_user().id).first_or_404()
    if request.method == "PATCH":
        data = request.get_json(silent=True) or {}
        for field in ("display_name", "trade", "secondary_services", "bio", "city", "area", "languages"):
            if field in data: setattr(profile, field, str(data[field]).strip())
        for field in ("years_experience", "radius_km"):
            if field in data: setattr(profile, field, max(int(data[field]), 0))
        if "starting_price" in data: profile.starting_price = data["starting_price"]
        if "instant_booking" in data: profile.instant_booking = bool(data["instant_booking"])
        db.session.commit()
    return jsonify({"artisan": {**profile.search_card(0), "bio": profile.bio, "city": profile.city, "area": profile.area, "languages": profile.languages, "radius_km": profile.radius_km, "verification_status": profile.verification_status, "available": profile.available}})


@bp.route("/artisans/me/availability", methods=["GET", "PUT"])
@role_required(Role.ARTISAN)
def availability():
    profile = ArtisanProfile.query.filter_by(user_id=current_user().id).first_or_404()
    if request.method == "PUT":
        data = request.get_json(silent=True) or {}; rows = data.get("items", [])
        Availability.query.filter_by(artisan_id=profile.id).delete()
        for row in rows:
            from datetime import time
            start_h, start_m = map(int, row["start_time"].split(":")); end_h, end_m = map(int, row["end_time"].split(":"))
            db.session.add(Availability(artisan_id=profile.id, weekday=int(row["weekday"]), start_time=time(start_h, start_m), end_time=time(end_h, end_m), active=bool(row.get("active", True))))
        profile.available = any(row.get("active", True) for row in rows); db.session.commit()
    items = Availability.query.filter_by(artisan_id=profile.id).order_by(Availability.weekday).all()
    return jsonify({"items": [{"weekday": row.weekday, "start_time": row.start_time.strftime("%H:%M"), "end_time": row.end_time.strftime("%H:%M"), "active": row.active} for row in items]})


@bp.route("/artisans/me/portfolio", methods=["GET", "POST"])
@role_required(Role.ARTISAN)
def portfolio():
    profile = ArtisanProfile.query.filter_by(user_id=current_user().id).first_or_404()
    if request.method == "POST":
        file = request.files.get("file")
        try: url = upload_file(file, profile.id, "portfolio")
        except (ValueError, RuntimeError) as error: return jsonify({"message": str(error)}), 422
        item = PortfolioItem(artisan_id=profile.id, title=request.form.get("title", "Untitled work").strip(), description=request.form.get("description", "").strip(), service=request.form.get("service", profile.trade).strip(), media_url=url, media_type="video" if file.mimetype.startswith("video") else "image", before_after=request.form.get("before_after"))
        db.session.add(item); db.session.commit(); return jsonify({"item": {"id": item.id, "status": item.moderation_status, "media_url": item.media_url}}), 201
    rows = PortfolioItem.query.filter_by(artisan_id=profile.id).order_by(PortfolioItem.created_at.desc()).all()
    return jsonify({"items": [{"id": row.id, "title": row.title, "service": row.service, "media_url": row.media_url, "status": row.moderation_status} for row in rows]})


@bp.route("/artisans/me/verifications", methods=["GET", "POST"])
@role_required(Role.ARTISAN)
def verifications():
    profile = ArtisanProfile.query.filter_by(user_id=current_user().id).first_or_404()
    allowed = {"government_id", "live_selfie", "trade_proof", "payout_name"}
    if request.method == "POST":
        kind = str(request.form.get("kind") or "")
        if kind not in allowed: return jsonify({"message": "Unsupported verification type"}), 422
        row = Verification.query.filter_by(artisan_id=profile.id, kind=kind).first()
        if row and row.status == "approved": return jsonify({"message": "Approved verification cannot be replaced without an admin request"}), 409
        if not row: row = Verification(artisan_id=profile.id, kind=kind)
        if kind == "payout_name":
            value = str(request.form.get("value") or "").strip()
            if not value: return jsonify({"message": "Payout account name is required"}), 422
            row.provider_reference = value[:120]
        else:
            try: row.file_url = upload_file(request.files.get("file"), profile.id, "verification", private=True)
            except (ValueError, RuntimeError) as error: return jsonify({"message": str(error)}), 422
        row.status, row.decision_reason, row.decided_at, row.reviewer_id = "pending", None, None, None
        db.session.add(row); db.session.commit(); return jsonify({"id": row.id, "kind": row.kind, "status": row.status}), 201
    rows = Verification.query.filter_by(artisan_id=profile.id).all()
    return jsonify({"profile_status": profile.verification_status, "items": [{"id": row.id, "kind": row.kind, "status": row.status, "decision_reason": row.decision_reason, "updated_at": row.updated_at.isoformat()} for row in rows]})

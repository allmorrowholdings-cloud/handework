from datetime import date, datetime, timezone
from math import isfinite
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from ..services.email_delivery import queue_email
from ..extensions import db, limiter
from ..models import ArtisanProfile, Availability, FileAsset, PortfolioItem, Role, Verification
from ..security import current_user, role_required
from ..services.distance import haversine_km
from ..services.maps import geocode, places, point, LocationUnavailable
from ..services.matching import matching_score
from ..services.storage import private_download_url, upload_file, metadata_for, delete_object
from ..services.workproof import public_workproof

bp = Blueprint("marketplace", __name__)


def parse_coordinates(value):
    try:
        latitude, longitude = [float(part.strip()) for part in value.split(",", 1)]
        if -90 <= latitude <= 90 and -180 <= longitude <= 180: return latitude, longitude
    except (ValueError, AttributeError): pass
    return None


@bp.get("/services")
def services():
    profiles = db.session.query(ArtisanProfile.trade, ArtisanProfile.secondary_services).filter_by(verification_status="approved").distinct()
    names = {name.strip() for trade, secondary in profiles for name in [trade, *(secondary or "").split(",")] if name.strip()}
    return jsonify({"items": sorted(names, key=str.casefold)})


TRADE_TERMS = {
    "Plumbing": ("plumb", "leaking tap", "tap is leaking", "burst pipe", "pluming"),
    "Electrical": ("electric", "lights keep going off", "socket", "electrical wiring"),
    "Carpentry": ("carpent", "custom furniture", "cabinet"),
    "Tailoring": ("tailor", "dressmaker", "dress made", "alteration"),
    "AC repair": ("air conditioning", "ac repair", "ac is not cooling", "cooling"),
    "Cleaning": ("clean", "housekeep"),
    "Hairdressing": ("hair", "braid", "barber"),
}


def search_terms(service):
    query = service.casefold().strip()
    for name, terms in TRADE_TERMS.items():
        if name.casefold() == query or any(term in query for term in terms):
            return (name, *terms)
    return (service,)


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
    if request.args.get("coordinates") and not coordinates:
        return jsonify(message="Invalid search coordinates"),422
    try:
        weekday = date.fromisoformat(request.args["date"]).weekday() if request.args.get("date") else None
    except ValueError:
        return jsonify(message="Date must use YYYY-MM-DD"),422
    rows = ranked_artisans(service,coordinates,distance_limit,request.args.get("location"),weekday)
    return jsonify({"items": rows[:50], "meta": {"service": service, "coordinates_used": bool(coordinates), "distance_km": distance_limit}})


def ranked_artisans(service,coordinates,distance_limit,location=None,weekday=None):
    query = ArtisanProfile.query.filter_by(verification_status="approved", available=True)
    if service:
        query = query.filter(db.or_(*(
            column.icontains(term, autoescape=True) for term in search_terms(service)
            for column in (ArtisanProfile.trade, ArtisanProfile.secondary_services)
        )))
    if location and not coordinates:
        terms = [part.strip() for part in location.split(",") if part.strip()]
        for term in terms:
            query = query.filter(db.or_(ArtisanProfile.area.icontains(term, autoescape=True), ArtisanProfile.city.icontains(term, autoescape=True)))
    rows = []
    if coordinates:
        band = distance_limit/110 + .001
        query = query.filter(ArtisanProfile.latitude.between(coordinates[0]-band, coordinates[0]+band))
    if weekday is not None:
        query=query.filter(ArtisanProfile.id.in_(db.select(Availability.artisan_id).where(
            Availability.weekday==weekday, Availability.active.is_(True))))
    for profile in query.yield_per(200):
        if coordinates and profile.latitude is not None and profile.longitude is not None:
            distance = haversine_km(coordinates[0], coordinates[1], profile.latitude, profile.longitude)
        elif coordinates:
            continue
        else:
            distance = None
        if distance is not None and distance > min(distance_limit, profile.radius_km): continue
        card = profile.search_card(distance)
        card["avatar_url"] = private_download_url(profile.avatar_url,300) if profile.avatar_url else None
        card.update(area=profile.area, city=profile.city)
        card["match_score"] = matching_score(text_match=1 if service else .5, distance_km=distance, radius_km=profile.radius_km, rating=profile.rating_average, completion_rate=profile.completion_rate, available=profile.available, response_minutes=profile.response_minutes)
        rows.append(card)
    rows.sort(key=lambda item: (-item["match_score"], item["distance_km"] if item["distance_km"] is not None else float("inf"), item["id"]))
    return rows



@bp.get("/artisans/<artisan_id>")
def artisan_detail(artisan_id):
    profile = ArtisanProfile.query.filter_by(id=artisan_id, verification_status="approved").first_or_404()
    portfolio = PortfolioItem.query.filter_by(artisan_id=profile.id, moderation_status="approved").order_by(PortfolioItem.created_at.desc()).all()
    return jsonify({"artisan": {**profile.search_card(None), "avatar_url":private_download_url(profile.avatar_url,300) if profile.avatar_url else None, "bio": profile.bio, "years_experience": profile.years_experience, "city": profile.city, "area": profile.area, "languages": profile.languages, "radius_km": profile.radius_km}, "workproof": public_workproof(profile), "portfolio": [{"id": item.id, "title": item.title, "description": item.description, "service": item.service, "media_url": private_download_url(item.media_url,300), "media_type": item.media_type, "before_after": item.before_after} for item in portfolio]})


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
        if data.get("latitude") is not None or data.get("longitude") is not None:
            try:
                profile.latitude, profile.longitude = point(data.get("latitude"),data.get("longitude"))
            except ValueError:
                return jsonify(message="Invalid service location"),422
        if "starting_price" in data: profile.starting_price = data["starting_price"]
        if "instant_booking" in data: profile.instant_booking = bool(data["instant_booking"])
        db.session.commit()
    return jsonify({"artisan": {**profile.search_card(None), "avatar_url":private_download_url(profile.avatar_url,300) if profile.avatar_url else None, "bio": profile.bio, "city": profile.city, "area": profile.area, "languages": profile.languages, "radius_km": profile.radius_km, "latitude":float(profile.latitude) if profile.latitude is not None else None,"longitude":float(profile.longitude) if profile.longitude is not None else None,"verification_status": profile.verification_status, "available": profile.available}})


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
        replace_id=str(request.form.get("replace_id") or "")
        existing=PortfolioItem.query.filter_by(id=replace_id,artisan_id=profile.id).first() if replace_id else None
        if replace_id and not existing: return jsonify({"message":"Portfolio item not found"}),404
        try:
            stored = upload_file(file, current_user().id, "portfolio", private=True)
            asset=FileAsset(owner_id=current_user().id,purpose="portfolio",**metadata_for(stored));db.session.add(asset);db.session.flush()
            if existing:
                old_asset=db.session.get(FileAsset,existing.file_asset_id) if existing.file_asset_id else None
                existing.file_asset_id=asset.id;existing.media_url=asset.url;existing.media_type="video" if file.mimetype.startswith("video") else "image";existing.moderation_status="pending"
            else:
                existing=PortfolioItem(artisan_id=profile.id,title=request.form.get("title", "Untitled work").strip(),description=request.form.get("description", "").strip(),service=request.form.get("service",profile.trade).strip(),media_url=asset.url,file_asset_id=asset.id,media_type="video" if file.mimetype.startswith("video") else "image",before_after=request.form.get("before_after"));db.session.add(existing);old_asset=None
            if old_asset:
                asset.replaces_asset_id = old_asset.id
                old_asset.deleted_at = datetime.now(timezone.utc)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            if "stored" in locals():
                try: delete_object(stored.url)
                except Exception: current_app.logger.exception("Invalid portfolio upload cleanup failed")
            return jsonify({"message": str(error)}), 422
        except RuntimeError as error:
            db.session.rollback()
            if "stored" in locals():
                try: delete_object(stored.url)
                except Exception: current_app.logger.exception("Failed portfolio upload cleanup failed")
            return jsonify({"message": str(error)}), 503
        except Exception:
            db.session.rollback()
            if "stored" in locals():
                try: delete_object(stored.url)
                except Exception: current_app.logger.exception("Portfolio transaction cleanup failed")
            raise
        if old_asset:
            try: delete_object(old_asset.url)
            except Exception: current_app.logger.exception("Replaced portfolio file cleanup failed")
        return jsonify({"item": {"id": existing.id, "status": existing.moderation_status, "media_url": private_download_url(existing.media_url,300)}}), 201
    rows = PortfolioItem.query.filter_by(artisan_id=profile.id).order_by(PortfolioItem.created_at.desc()).all()
    return jsonify({"items": [{"id": row.id, "title": row.title, "service": row.service, "media_url": private_download_url(row.media_url,300), "status": row.moderation_status} for row in rows]})


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
        stored = None
        old_asset = None
        if kind == "payout_name":
            value = str(request.form.get("value") or "").strip()
            if not value:
                return jsonify(message="Payout account name is required"), 422
            row.provider_reference = value[:120]
        else:
            try:
                stored = upload_file(request.files.get("file"), current_user().id, kind)
            except ValueError as error:
                return jsonify(message=str(error)), 422
            except RuntimeError as error:
                return jsonify(message=str(error)), 503
        try:
            if stored:
                old_asset = db.session.get(FileAsset, row.file_asset_id) if row.file_asset_id else None
                asset = FileAsset(owner_id=current_user().id, purpose=kind,
                                  replaces_asset_id=row.file_asset_id, **metadata_for(stored))
                db.session.add(asset)
                db.session.flush()
                row.file_url, row.file_asset_id = asset.url, asset.id
                if old_asset:
                    old_asset.deleted_at = datetime.now(timezone.utc)
            row.status, row.decision_reason, row.decided_at, row.reviewer_id = "pending", None, None, None
            db.session.add(row)
            queue_email(profile.user, "Verification submitted", f"Your {kind.replace('_', ' ')} verification is pending review.")
            db.session.commit()
        except Exception:
            db.session.rollback()
            if stored:
                try: delete_object(stored.url)
                except Exception: current_app.logger.exception("Verification transaction cleanup failed")
            raise
        if old_asset:
            try: delete_object(old_asset.url)
            except Exception: current_app.logger.exception("Replaced verification object cleanup failed")
        return jsonify({"id": row.id, "kind": row.kind, "status": row.status}), 201
    rows = Verification.query.filter_by(artisan_id=profile.id).all()
    return jsonify({"profile_status": profile.verification_status, "items": [{"id": row.id, "kind": row.kind, "status": row.status, "decision_reason": row.decision_reason, "updated_at": row.updated_at.isoformat()} for row in rows]})

@bp.get("/locations/search")
@bp.get("/locations/reverse")
@limiter.limit("30 per minute")
def location_search():
    coords=parse_coordinates(request.args.get("coordinates",""))
    query=request.args.get("q","").strip()
    reverse=request.path.endswith("/reverse")
    if (reverse and not coords) or (not reverse and not 2<=len(query)<=250):
        return jsonify(message="Enter a valid address or coordinate pair"),422
    try:
        return jsonify(items=places(query=query,coordinates=coords if reverse else None))
    except LocationUnavailable as exc:
        return jsonify(message=str(exc)),503

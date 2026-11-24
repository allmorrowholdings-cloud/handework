import secrets
from datetime import datetime, timezone, timedelta
from email_validator import validate_email, EmailNotValidError
import phonenumbers
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity, jwt_required
from ..extensions import db, limiter
from ..models import ArtisanProfile, LoginSession, Role, User

bp = Blueprint("auth", __name__)


def normalize_email(value):
    try: return validate_email(str(value or "").strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError: return None


def normalize_phone(value):
    try:
        parsed = phonenumbers.parse(str(value or ""), "GH")
        if not phonenumbers.is_valid_number(parsed): return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException: return None



def browser_tokens(user, session_id):
    return {
        "access_token": create_access_token(identity=user.id, additional_claims={"sid": session_id, "role": user.role.value}),
        "refresh_token": create_refresh_token(identity=user.id, additional_claims={"sid": session_id}, expires_delta=timedelta(days=1)),
    }


def session_for(user):
    if (request.get_json(silent=True) or {}).get("client") == "web":
        session = LoginSession(user_id=user.id)
        db.session.add(session)
        db.session.commit()
        return {**browser_tokens(user, session.id), "user": user.public()}

    return {"access_token": create_access_token(identity=user.id, additional_claims={"role": user.role.value}), "refresh_token": create_refresh_token(identity=user.id), "user": user.public()}


def create_user(data, role):
    email, phone = normalize_email(data.get("email")), normalize_phone(data.get("phone"))
    if not email: return None, (jsonify({"message": "Enter a valid email address", "code": "invalid_email"}), 422)
    if not phone: return None, (jsonify({"message": "Enter a valid mobile number", "code": "invalid_phone"}), 422)
    password = str(data.get("password") or "")
    if len(password) < 8: return None, (jsonify({"message": "Password must have at least 8 characters", "code": "weak_password"}), 422)
    if User.query.filter((User.email == email) | (User.phone == phone)).first(): return None, (jsonify({"message": "An account already uses this email or mobile number", "code": "account_exists"}), 409)
    user = User(email=email, phone=phone, first_name=str(data.get("first_name") or "").strip(), last_name=str(data.get("last_name") or "").strip(), role=role, referral_code=secrets.token_hex(4).upper())
    if not user.first_name or not user.last_name: return None, (jsonify({"message": "First and last name are required", "code": "missing_name"}), 422)
    user.set_password(password)
    db.session.add(user); db.session.flush()
    return user, None


@bp.post("/auth/register")
@limiter.limit("5 per minute")
def register():
    user, error = create_user(request.get_json(silent=True) or {}, Role.CUSTOMER)
    if error: return error
    db.session.commit(); return jsonify(session_for(user)), 201


@bp.post("/auth/register-artisan")
@limiter.limit("5 per minute")
def register_artisan():
    data = request.get_json(silent=True) or {}
    user, error = create_user(data, Role.ARTISAN)
    if error: return error
    trade, city, area = str(data.get("trade") or "").strip(), str(data.get("city") or "").strip(), str(data.get("area") or "").strip()
    if not all((trade, city, area)): db.session.rollback(); return jsonify({"message": "Trade, city and area are required", "code": "incomplete_artisan_profile"}), 422
    profile = ArtisanProfile(user_id=user.id, display_name=f"{user.first_name} {user.last_name}".strip(), trade=trade, secondary_services=str(data.get("secondary_services") or ""), bio=str(data.get("bio") or ""), years_experience=max(int(data.get("years_experience") or 0), 0), city=city, area=area, radius_km=min(max(int(data.get("radius_km") or 10), 1), 100))
    db.session.add(profile); db.session.commit(); return jsonify(session_for(user)), 201


@bp.post("/auth/login")
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}; email = normalize_email(data.get("email"))
    user = User.query.filter_by(email=email).first() if email else None
    if not user or not user.check_password(str(data.get("password") or "")): return jsonify({"message": "Email or password is incorrect", "code": "invalid_credentials"}), 401
    if user.status != "active": return jsonify({"message": "This account cannot sign in", "code": "account_unavailable"}), 403
    user.last_login_at = datetime.now(timezone.utc); db.session.commit(); return jsonify(session_for(user))


@bp.post("/auth/refresh")
@jwt_required(refresh=True)
def refresh():
    user = db.session.get(User, get_jwt_identity())
    if not user or user.status != "active": return jsonify({"message": "Account is unavailable"}), 401
    sid = get_jwt().get("sid")
    if sid:
        now = datetime.now(timezone.utc)
        updated = LoginSession.query.filter(LoginSession.id == sid, LoginSession.user_id == user.id,
                                            LoginSession.last_active > now - timedelta(days=1)).update({"last_active": now}, synchronize_session=False)
        if not updated:
            return jsonify({"message": "Please sign in again."}), 401
        db.session.commit()
        return jsonify(browser_tokens(user, sid))
    if (request.get_json(silent=True) or {}).get("client") == "web":
        return jsonify(session_for(user))
    return jsonify({"access_token": create_access_token(identity=user.id, additional_claims={"role": user.role.value})})


@bp.post("/auth/logout")
@jwt_required(verify_type=False)
def logout():
    sid = get_jwt().get("sid")
    if sid:
        LoginSession.query.filter_by(id=sid, user_id=get_jwt_identity()).delete()
        db.session.commit()
    return "", 204


@bp.route("/auth/me", methods=["GET", "PATCH"])
@jwt_required()
def me():
    user = db.session.get(User, get_jwt_identity())
    if not user: return jsonify({"message": "Account not found"}), 404
    if request.method == "PATCH":
        data = request.get_json(silent=True) or {}
        for field in ("first_name", "last_name"):
            if field in data:
                value = str(data[field] or "").strip()
                if not value: return jsonify({"message": f"{field.replace('_', ' ').title()} is required"}), 422
                setattr(user, field, value[:80])
        if "phone" in data:
            phone = normalize_phone(data["phone"])
            if not phone: return jsonify({"message": "Enter a valid mobile number"}), 422
            if User.query.filter(User.phone == phone, User.id != user.id).first(): return jsonify({"message": "Another account already uses this mobile number"}), 409
            user.phone = phone
        if "notification_preferences" in data:
            incoming = data.get("notification_preferences") or {}
            current = user.notification_preferences or {}
            user.notification_preferences = {key: bool(incoming.get(key, current.get(key, False))) for key in ("push", "whatsapp", "sms")}
        db.session.commit()
    return jsonify({"user": user.public()})

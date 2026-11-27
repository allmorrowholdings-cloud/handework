import secrets
from datetime import datetime, timezone, timedelta
from email_validator import validate_email, EmailNotValidError
import phonenumbers
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity, jwt_required
from ..extensions import db, limiter
from ..models import ArtisanProfile, LoginSession, Notification, Role, User
from ..services.email_delivery import ACCOUNT_SUBJECTS, CODE_LIFETIME, account_code, enabled, queue_account_email, utc

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



def browser_tokens(user, session_id, installed=False):
    return {
        "access_token": create_access_token(identity=user.id, additional_claims={"sid": session_id, "role": user.role.value, "installed": installed}),
        "refresh_token": create_refresh_token(identity=user.id, additional_claims={"sid": session_id, "installed": installed}, expires_delta=timedelta(days=30 if installed else 1)),
    }


def session_for(user):
    if (request.get_json(silent=True) or {}).get("client") in ("web", "installed"):
        installed = (request.get_json(silent=True) or {}).get("client") == "installed"
        session = LoginSession(user_id=user.id)
        db.session.add(session)
        db.session.flush()
        result = {**browser_tokens(user, session.id, installed=installed), "user": user.public()}
        db.session.commit()
        return result

    return {"access_token": create_access_token(identity=user.id, additional_claims={"role": user.role.value}), "refresh_token": create_refresh_token(identity=user.id), "user": user.public()}


def create_user(data, role):
    email, phone = normalize_email(data.get("email")), normalize_phone(data.get("phone"))
    if not email: return None, (jsonify({"message": "Enter a valid email address", "code": "invalid_email"}), 422)
    if not phone: return None, (jsonify({"message": "Enter a valid mobile number", "code": "invalid_phone"}), 422)
    password = str(data.get("password") or "")
    if len(password) < 12 or len(password) > 128: return None, (jsonify({"message": "Choose a unique password or passphrase of 12 to 128 characters", "code": "weak_password"}), 422)
    if User.query.filter((User.email == email) | (User.phone == phone)).first(): return None, (jsonify({"message": "An account already uses this email or mobile number", "code": "account_exists"}), 409)
    user = User(email=email, phone=phone, first_name=str(data.get("first_name") or "").strip(), last_name=str(data.get("last_name") or "").strip(), role=role, referral_code=secrets.token_hex(4).upper())
    if not user.first_name or not user.last_name: return None, (jsonify({"message": "First and last name are required", "code": "missing_name"}), 422)
    user.set_password(password)
    db.session.add(user); db.session.flush()
    queue_account_email(user, 'verify')
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
    from ..models import UserTotp
    from ..services.totp import authenticate_second_factor

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(message="Invalid login request"), 422

    email = normalize_email(data.get("email"))

    user = User.query.filter_by(
        email=email
    ).with_for_update().first() if email else None

    if not user or not user.check_password(
        str(data.get("password") or "")
    ):
        return jsonify({
            "message": "Email or password is incorrect",
            "code": "invalid_credentials"
        }), 401

    if user.status != "active":
        return jsonify({
            "message": "This account cannot sign in",
            "code": "account_unavailable"
        }), 403

    row = db.session.get(UserTotp, user.id)

    if row and row.enabled_at:
        supplied = str(data.get("totp_code") or "").strip()

        if not supplied:
            return jsonify({
                "message": "Enter your authenticator or recovery code",
                "code": "totp_required"
            }), 401

        try:
            result = authenticate_second_factor(
                row, supplied
            )
        except Exception:
            db.session.rollback()
            return jsonify({
                "message": "Authenticator temporarily unavailable",
                "code": "totp_unavailable"
            }), 503

        if result != "accepted":
            db.session.commit()

            if result == "locked":
                return jsonify({
                    "message": "Too many attempts. Try again later.",
                    "code": "totp_locked"
                }), 429

            return jsonify({
                "message": "Invalid or previously used authentication code",
                "code": "totp_invalid"
            }), 401

    user.last_login_at = datetime.now(timezone.utc)

    result = session_for(user)
    db.session.commit()

    return jsonify(result)


@bp.post("/auth/refresh")
@jwt_required(refresh=True)
def refresh():
    user = User.query.filter_by(
        id=get_jwt_identity()
    ).populate_existing().with_for_update().first()

    if not user or user.status != "active":
        return jsonify({
            "message": "Account is unavailable"
        }), 401

    if get_jwt().get("session_version", 0) != user.session_version:
        return jsonify({
            "message": "Your session has expired. Please sign in again.",
            "code": "session_revoked"
        }), 401

    sid = get_jwt().get("sid")
    if sid:
        now = datetime.now(timezone.utc)
        updated = LoginSession.query.filter(LoginSession.id == sid, LoginSession.user_id == user.id,
                                            LoginSession.last_active > now - timedelta(days=30 if get_jwt().get("installed") else 1)).update({"last_active": now}, synchronize_session=False)
        if not updated:
            return jsonify({"message": "Please sign in again."}), 401
        db.session.commit()
        return jsonify(browser_tokens(user, sid, installed=bool(get_jwt().get("installed"))))
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
    query = User.query.filter_by(id=get_jwt_identity())
    if request.method == "PATCH":
        query = query.with_for_update()
    user = query.first()
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
            if user.phone != phone:
                from ..services.phone_verification import (
                    verification_enabled, invalidate_code
                )
                if verification_enabled():
                    try:
                        invalidate_code(user.id)
                    except Exception:
                        db.session.rollback()
                        return jsonify(message="Phone update temporarily unavailable"), 503
                user.phone_verified_at = None
                user.phone = phone
        if "notification_preferences" in data:
            incoming = data.get("notification_preferences") or {}
            current = user.notification_preferences or {}
            user.notification_preferences = {key: bool(incoming.get(key, current.get(key, False))) for key in ("push", "whatsapp", "sms")}
            user.notification_preferences = {**user.notification_preferences, "email": bool(incoming.get("email", current.get("email", True)))}
        db.session.commit()
    return jsonify({"user": user.public()})


@bp.post("/auth/email/<action>/request")
@limiter.limit("5 per hour")
def request_account_code(action):
    if action not in ACCOUNT_SUBJECTS:
        return jsonify(message="Unknown account action"), 404
    if not enabled():
        return jsonify(message="Email delivery is unavailable"), 503
    email = normalize_email((request.get_json(silent=True) or {}).get("email"))
    user = User.query.filter_by(email=email, status="active").with_for_update().first()
    if user and (action == "reset" or not user.email_verified_at):
        recent = Notification.query.filter_by(user_id=user.id, channel="email", title=ACCOUNT_SUBJECTS[action]).filter(
            Notification.created_at > datetime.now(timezone.utc) - timedelta(minutes=2)).first()
        if not recent:
            queue_account_email(user, action)
            db.session.commit()
    return jsonify(message="If your account is eligible, check your email for a code."), 202


@bp.post("/auth/email/<action>/confirm")
@limiter.limit("10 per hour")
def confirm_account_code(action):
    if action not in ACCOUNT_SUBJECTS:
        return jsonify(message="Unknown account action"), 404
    data = request.get_json(silent=True) or {}
    user = User.query.filter_by(email=normalize_email(data.get("email")), status="active").with_for_update().first()
    row = Notification.query.filter_by(user_id=user.id, channel="email", title=ACCOUNT_SUBJECTS[action],
                                       read_at=None).order_by(Notification.created_at.desc()).first() if user else None
    now = datetime.now(timezone.utc)
    supplied = str(data.get("code") or "").strip().lower().encode()
    if (not row or row.status not in {"sending", "unknown", "sent"}
            or utc(row.created_at) + CODE_LIFETIME <= now
            or not secrets.compare_digest(supplied, account_code(row, user).encode())):
        return jsonify(message="This code is invalid or expired"), 422
    if action == "reset":
        password = data.get("password")
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            return jsonify(message="Password must contain 12 to 128 characters"), 422
        user.set_password(password)
        user.session_version += 1
        LoginSession.query.filter_by(user_id=user.id).delete()
    else:
        user.email_verified_at = now
    row.read_at = now
    db.session.commit()
    return jsonify(message="Password updated" if action == "reset" else "Email verified")



@bp.post("/auth/phone/request")
@jwt_required()
@limiter.limit("5 per minute")
def request_phone_verification():
    from ..services.phone_verification import (
        request_code, verification_enabled
    )

    if not verification_enabled():
        return jsonify(message="Phone verification is unavailable"), 503

    user = User.query.filter_by(
        id=get_jwt_identity(), status="active"
    ).with_for_update().first()

    if not user:
        return jsonify(message="Account unavailable"), 403

    if user.phone_verified_at:
        return jsonify(message="Phone already verified"), 200

    try:
        accepted = request_code(user.id, user.phone)
    except ValueError:
        db.session.rollback()
        return jsonify(message="Unsupported phone number"), 422
    except Exception:
        db.session.rollback()
        return jsonify(message="Verification delivery temporarily unavailable"), 503

    db.session.commit()

    if not accepted:
        return jsonify(message="Verification limit reached. Try again later."), 429

    return jsonify(message="Verification code submitted"), 202


@bp.post("/auth/phone/confirm")
@jwt_required()
@limiter.limit("10 per minute")
def confirm_phone_verification():
    from ..services.phone_verification import (
        confirm_code, verification_enabled
    )

    if not verification_enabled():
        return jsonify(message="Phone verification is unavailable"), 503

    user = User.query.filter_by(
        id=get_jwt_identity(), status="active"
    ).with_for_update().first()

    if not user:
        return jsonify(message="Account unavailable"), 403

    if user.phone_verified_at:
        return jsonify(message="Phone already verified", user=user.public())

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(message="Invalid request"), 422

    code = str(data.get("code") or "").strip()

    try:
        verified = confirm_code(user.id, user.phone, code)
    except Exception:
        db.session.rollback()
        return jsonify(message="Verification temporarily unavailable"), 503

    if not verified:
        db.session.rollback()
        return jsonify(message="Invalid or expired verification code"), 422

    user.phone_verified_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(message="Phone verified", user=user.public())

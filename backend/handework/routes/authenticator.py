import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..extensions import db, limiter
from ..models import (
    User,
    UserTotp,
    UserTotpRecoveryCode,
    LoginSession
)
from ..services.totp import (
    totp_enabled,
    admin_totp_required,
    create_secret,
    encrypt_secret,
    decrypt_secret,
    provisioning_uri,
    create_qr_code,
    matching_step,
    create_recovery_codes,
    hash_recovery_code
)

bp = Blueprint("authenticator", __name__)


def utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def locked_user():
    return User.query.filter_by(
        id=get_jwt_identity(),
        status="active"
    ).with_for_update().first()


def secure_response(payload, status=200):
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response


def invalidate_sessions(user):
    user.session_version += 1
    LoginSession.query.filter_by(user_id=user.id).delete()


@bp.get("/auth/totp/status")
@jwt_required()
def authenticator_status():
    user = db.session.get(User, get_jwt_identity())

    if not user or user.status != "active":
        return jsonify(message="Account unavailable"), 403

    row = db.session.get(UserTotp, user.id)

    return secure_response({
        "available": totp_enabled(),
        "required": (
            user.role.value == "admin"
            and admin_totp_required()
        ),
        "enabled": bool(row and row.enabled_at),
        "recovery_codes_remaining": (
            UserTotpRecoveryCode.query.filter_by(
                user_id=user.id,
                used_at=None
            ).count() if row and row.enabled_at else 0
        )
    })


@bp.post("/auth/totp/setup")
@jwt_required()
@limiter.limit("5 per hour")
def authenticator_setup():
    if not totp_enabled():
        return jsonify(message="Authenticator setup unavailable"), 503

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(message="Invalid request"), 422

    user = locked_user()

    if not user:
        return jsonify(message="Account unavailable"), 403

    password = data.get("password")

    if not isinstance(password, str) or not user.check_password(password):
        return jsonify(message="Current password is incorrect"), 403

    row = db.session.get(UserTotp, user.id)

    if row and row.enabled_at:
        return jsonify(message="Authenticator is already enabled"), 409

    if not row:
        row = UserTotp(user_id=user.id)
        db.session.add(row)

    now = datetime.now(timezone.utc)

    if row.locked_until and utc(row.locked_until) > now:
        return jsonify(message="Too many attempts. Try again later."), 429

    secret = create_secret()

    row.pending_secret_encrypted = encrypt_secret(secret)
    row.pending_expires_at = now + timedelta(minutes=10)

    uri = provisioning_uri(secret, user.email)
    qr = create_qr_code(uri)

    db.session.commit()

    return secure_response({
        "secret": secret,
        "qr_code": qr,
        "expires_in": 600
    })


@bp.post("/auth/totp/enable")
@jwt_required()
@limiter.limit("10 per hour")
def authenticator_enable():
    if not totp_enabled():
        return jsonify(message="Authenticator setup unavailable"), 503

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(message="Invalid request"), 422

    user = locked_user()

    if not user:
        return jsonify(message="Account unavailable"), 403

    row = db.session.get(UserTotp, user.id)
    now = datetime.now(timezone.utc)

    if row and row.enabled_at:
        return jsonify(message="Authenticator is already enabled"), 409

    if (
        not row
        or not row.pending_secret_encrypted
        or not row.pending_expires_at
        or utc(row.pending_expires_at) <= now
    ):
        return jsonify(message="Setup expired. Start again."), 422

    if row.locked_until and utc(row.locked_until) > now:
        return jsonify(message="Too many attempts. Try again later."), 429

    if row.locked_until and utc(row.locked_until) <= now:
        row.failed_attempts = 0
        row.locked_until = None

    secret = decrypt_secret(row.pending_secret_encrypted)

    step = matching_step(
        secret,
        str(data.get("code") or ""),
        row.last_used_step
    )

    if step is None:
        row.failed_attempts += 1

        if row.failed_attempts >= 5:
            row.locked_until = now + timedelta(minutes=15)

        db.session.commit()

        return jsonify(message="Invalid authenticator code"), 422

    codes = create_recovery_codes()

    UserTotpRecoveryCode.query.filter_by(
        user_id=user.id
    ).delete()

    for code in codes:
        db.session.add(UserTotpRecoveryCode(
            user_id=user.id,
            code_hash=hash_recovery_code(code)
        ))

    row.secret_encrypted = row.pending_secret_encrypted
    row.pending_secret_encrypted = None
    row.pending_expires_at = None
    row.enabled_at = now
    row.last_used_step = step
    row.failed_attempts = 0
    row.locked_until = None

    invalidate_sessions(user)

    db.session.commit()

    return secure_response({
        "message": "Authenticator enabled",
        "enabled": True,
        "recovery_codes": codes,
        "sign_in_required": True
    })

@bp.post("/auth/totp/disable")
@jwt_required()
@limiter.limit("5 per hour")
def authenticator_disable():
    from ..services.totp import authenticate_second_factor

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(message="Invalid request"), 422

    user = locked_user()

    if not user:
        return jsonify(message="Account unavailable"), 403

    password = data.get("password")

    if not isinstance(password, str) or not user.check_password(password):
        return jsonify(message="Current password is incorrect"), 403

    from ..services.totp import admin_totp_required

    if user.role.value == "admin" and admin_totp_required():
        return jsonify(
            message="Administrators must keep two-factor authentication enabled"
        ), 403

    row = db.session.get(UserTotp, user.id)

    if not row or not row.enabled_at:
        return jsonify(message="Authenticator is not enabled"), 409

    result = authenticate_second_factor(
        row, str(data.get("code") or "").strip()
    )

    if result != "accepted":
        db.session.commit()

        return jsonify(
            message="Authentication code rejected"
        ), 429 if result == "locked" else 422

    UserTotpRecoveryCode.query.filter_by(
        user_id=user.id
    ).delete()

    db.session.delete(row)

    invalidate_sessions(user)
    db.session.commit()

    return secure_response({
        "message": "Authenticator disabled",
        "enabled": False,
        "sign_in_required": True
    })


@bp.post("/auth/totp/recovery/regenerate")
@jwt_required()
@limiter.limit("5 per hour")
def authenticator_regenerate_recovery():
    from ..services.totp import authenticate_second_factor

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(message="Invalid request"), 422

    user = locked_user()

    if not user:
        return jsonify(message="Account unavailable"), 403

    password = data.get("password")

    if not isinstance(password, str) or not user.check_password(password):
        return jsonify(message="Current password is incorrect"), 403

    row = db.session.get(UserTotp, user.id)

    if not row or not row.enabled_at:
        return jsonify(message="Authenticator is not enabled"), 409

    result = authenticate_second_factor(
        row, str(data.get("code") or "").strip()
    )

    if result != "accepted":
        db.session.commit()

        return jsonify(
            message="Authentication code rejected"
        ), 429 if result == "locked" else 422

    codes = create_recovery_codes()

    UserTotpRecoveryCode.query.filter_by(
        user_id=user.id
    ).delete()

    for code in codes:
        db.session.add(UserTotpRecoveryCode(
            user_id=user.id,
            code_hash=hash_recovery_code(code)
        ))

    invalidate_sessions(user)
    db.session.commit()

    return secure_response({
        "message": "Recovery codes regenerated",
        "recovery_codes": codes,
        "sign_in_required": True
    })

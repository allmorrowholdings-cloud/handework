"""Verified Google Identity Services authentication for handEwork web/PWA.

Google identities are linked by stable `sub`, never auto-linked by matching email.
"""
import os
import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from ..extensions import db, limiter
from ..models import GoogleIdentity, User, UserTotp, Role
from ..services.totp import authenticate_second_factor
from .auth import normalize_email, normalize_phone, session_for

bp = Blueprint("google_auth", __name__)


def verified_identity(token):
    audience = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not audience or not isinstance(token, str) or len(token) > 8192 or not token:
        return None
    try:
        claims = id_token.verify_oauth2_token(token, GoogleRequest(), audience)
    except (ValueError, Exception):
        return None
    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        return None
    if claims.get("email_verified") is not True:
        return None
    if not claims.get("sub") or not normalize_email(claims.get("email")):
        return None
    return claims


def requires_totp(user, data):
    row = db.session.get(UserTotp, user.id)
    if not row or not row.enabled_at:
        return None
    code = str(data.get("totp_code") or "").strip()
    if not code:
        return (jsonify(message="Enter your authenticator or recovery code", code="totp_required"), 401)
    try:
        result = authenticate_second_factor(row, code)
    except Exception:
        db.session.rollback()
        return (jsonify(message="Authenticator temporarily unavailable", code="totp_unavailable"), 503)
    if result != "accepted":
        db.session.commit()
        return (jsonify(message="Authentication code rejected", code="totp_locked" if result == "locked" else "totp_invalid"), 429 if result == "locked" else 401)
    return None


@bp.post("/auth/google/login")
@limiter.limit("10 per minute")
def google_login():
    data = request.get_json(silent=True) or {}
    claims = verified_identity(data.get("credential"))
    if not claims:
        return jsonify(message="Google sign-in is unavailable or verification failed", code="invalid_google_token"), 401
    linked = GoogleIdentity.query.filter_by(google_sub=claims["sub"]).first()
    if not linked:
        existing = User.query.filter_by(email=normalize_email(claims["email"])).first()
        if existing:
            return jsonify(message="Sign in with your password, then connect Google in Account security.", code="google_link_required"), 409
        return jsonify(message="Complete account registration to continue.", code="google_registration_required", profile={"first_name": str(claims.get("given_name") or "")[:80], "last_name": str(claims.get("family_name") or "")[:80], "email": normalize_email(claims.get("email"))}), 404
    user = db.session.get(User, linked.user_id)
    if not user or user.status != "active":
        return jsonify(message="Account unavailable", code="account_unavailable"), 403
    response = requires_totp(user, data)
    if response:
        return response
    user.last_login_at = datetime.now(timezone.utc)
    response = session_for(user)
    db.session.commit()
    return jsonify(response)


@bp.post("/auth/google/register")
@limiter.limit("5 per minute")
def google_register():
    data = request.get_json(silent=True) or {}
    claims = verified_identity(data.get("credential"))
    if not claims:
        return jsonify(message="Google identity could not be verified", code="invalid_google_token"), 401
    email = normalize_email(claims["email"])
    if GoogleIdentity.query.filter_by(google_sub=claims["sub"]).first() or User.query.filter_by(email=email).first():
        return jsonify(message="Account exists. Sign in or link your Google account.", code="account_exists"), 409
    phone = normalize_phone(data.get("phone"))
    if not phone:
        return jsonify(message="Enter a valid mobile number", code="invalid_phone"), 422
    if User.query.filter_by(phone=phone).first():
        return jsonify(message="An account already uses this mobile number", code="account_exists"), 409
    password = data.get("password")
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        return jsonify(message="Choose a unique password or passphrase of 12 to 128 characters", code="weak_password"), 422
    first = str(data.get("first_name") or claims.get("given_name") or "").strip()[:80]
    last = str(data.get("last_name") or claims.get("family_name") or "").strip()[:80]
    if not first or not last:
        return jsonify(message="First and last name are required", code="missing_name"), 422
    user = User(email=email, phone=phone, first_name=first, last_name=last, role=Role.CUSTOMER, referral_code=secrets.token_hex(4).upper())
    user.set_password(password)
    # Google is authoritative for gmail.com addresses and Workspace accounts; external addresses still require handEwork email verification.
    if email.endswith("@gmail.com") or claims.get("hd"):
        user.email_verified_at = datetime.now(timezone.utc)
    db.session.add(user)
    db.session.flush()
    db.session.add(GoogleIdentity(user_id=user.id, google_sub=claims["sub"]))
    db.session.commit()
    return jsonify(session_for(user)), 201


@bp.post("/auth/google/link")
@jwt_required()
@limiter.limit("5 per hour")
def google_link():
    data = request.get_json(silent=True) or {}
    user = db.session.get(User, get_jwt_identity())
    claims = verified_identity(data.get("credential"))
    if not user or user.status != "active":
        return jsonify(message="Account unavailable"), 403
    if not claims or normalize_email(claims["email"]) != user.email:
        return jsonify(message="Select the Google account matching your handEwork email", code="identity_mismatch"), 403
    if not user.check_password(str(data.get("password") or "")):
        return jsonify(message="Confirm your current handEwork password", code="password_required"), 403
    step = requires_totp(user, data)
    if step:
        return step
    if GoogleIdentity.query.filter_by(google_sub=claims["sub"]).first():
        return jsonify(message="This Google account is already connected", code="already_linked"), 409
    if GoogleIdentity.query.filter_by(user_id=user.id).first():
        return jsonify(message="This handEwork account already has a linked Google identity", code="already_linked"), 409
    db.session.add(GoogleIdentity(user_id=user.id, google_sub=claims["sub"]))
    db.session.commit()
    return jsonify(message="Google sign-in connected successfully")


@bp.post("/auth/google/verify-and-link")
@limiter.limit("5 per minute")
def google_verify_and_link():
    """Link an existing password account after Google proof + password + any enabled MFA.

    No account is created, no email-only linking and no MFA bypass.
    """
    data = request.get_json(silent=True) or {}
    claims = verified_identity(data.get("credential"))
    if not claims:
        return jsonify(message="Google identity could not be verified", code="invalid_google_token"), 401
    email = normalize_email(claims.get("email"))
    user = User.query.filter_by(email=email).with_for_update().first()
    if not user or not user.check_password(str(data.get("password") or "")):
        return jsonify(message="Existing account password is incorrect", code="invalid_credentials"), 401
    if user.status != "active":
        return jsonify(message="Account unavailable", code="account_unavailable"), 403
    existing_google = GoogleIdentity.query.filter_by(google_sub=claims["sub"]).first()
    if existing_google:
        return jsonify(message="Google identity already linked", code="already_linked"), 409
    if GoogleIdentity.query.filter_by(user_id=user.id).first():
        return jsonify(message="Another Google account is already linked", code="already_linked"), 409
    factor = requires_totp(user, data)
    if factor:
        return factor
    db.session.add(GoogleIdentity(user_id=user.id, google_sub=claims["sub"]))
    user.last_login_at = datetime.now(timezone.utc)
    result = session_for(user)
    db.session.commit()
    return jsonify(result)

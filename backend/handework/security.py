from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from .extensions import db
from datetime import datetime, timedelta, timezone
from .extensions import jwt
from .models import LoginSession, User


@jwt.additional_claims_loader
def session_version(identity):
    user = db.session.get(User, identity)
    return {"session_version": user.session_version if user else 0}


@jwt.token_in_blocklist_loader
def session_inactive(_header, claims):
    user = db.session.get(User, claims["sub"])
    if not user or claims.get("session_version", 0) != user.session_version:
        return True
    sid = claims.get("sid")
    if not sid:
        return False
    return LoginSession.query.filter(
        LoginSession.id == sid, LoginSession.user_id == claims["sub"],
        LoginSession.last_active > datetime.now(timezone.utc) - timedelta(days=1)
    ).first() is None


def current_user():
    return db.session.get(User, get_jwt_identity())


def role_required(*roles):
    allowed = {role.value if hasattr(role, "value") else role for role in roles}
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            verify_jwt_in_request()
            user = current_user()
            if not user or user.status != "active":
                return jsonify({"message": "Account is unavailable", "code": "account_unavailable"}), 401
            if user.role.value not in allowed:
                return jsonify({"message": "You do not have access to this action", "code": "forbidden"}), 403
            if user.role.value == "admin":
                from .models import UserTotp
                from .services.totp import admin_totp_required

                if admin_totp_required():
                    enrollment = db.session.get(UserTotp, user.id)

                    if not enrollment or not enrollment.enabled_at:
                        return jsonify({
                            "message": "Set up two-factor authentication in your account security settings.",
                            "code": "admin_totp_enrollment_required"
                        }), 403

            return fn(*args, **kwargs)
        return wrapped
    return decorator

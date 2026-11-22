from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from .extensions import db
from .models import User


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
            return fn(*args, **kwargs)
        return wrapped
    return decorator

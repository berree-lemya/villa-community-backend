from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from app.models import UserRole


def role_required(*roles):
    """Decorator that restricts access to users with specified roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") not in roles:
                return jsonify({"error": "Access forbidden: insufficient permissions"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    return role_required(UserRole.ADMIN)(fn)


def resident_required(fn):
    """Owners and tenants."""
    return role_required(UserRole.OWNER, UserRole.TENANT, UserRole.ADMIN)(fn)


def security_required(fn):
    return role_required(UserRole.SECURITY, UserRole.ADMIN)(fn)

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from datetime import datetime
from app import db, bcrypt
from app.models import User, UserRole

auth_bp = Blueprint("auth", __name__)

# ── Simple in-memory token blocklist (use Redis in production) ──
BLOCKLISTED_TOKENS = set()


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user (owner or tenant).
    Admin accounts are created only by existing admins.
    """
    data = request.get_json()
    required = ["name", "email", "password", "role"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields: name, email, password, role"}), 400

    role = data["role"].lower()
    allowed_self_roles = [UserRole.OWNER, UserRole.TENANT]
    if role not in allowed_self_roles:
        return jsonify({"error": "Role must be 'owner' or 'tenant'"}), 400

    if User.query.filter_by(email=data["email"].lower()).first():
        return jsonify({"error": "Email already registered"}), 409

    hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(
        name=data["name"].strip(),
        email=data["email"].lower().strip(),
        phone=data.get("phone"),
        password_hash=hashed_pw,
        role=role,
        villa_id=data.get("villa_id"),
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Registration successful",
        "user": user.to_dict()
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=data["email"].lower().strip()).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    if not user.is_active:
        return jsonify({"error": "Account is deactivated. Contact admin."}), 403

    # Record last login
    user.last_login = datetime.utcnow()
    db.session.commit()

    identity = str(user.id)
    additional_claims = {"role": user.role, "villa_id": user.villa_id}

    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=identity)

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Issue a new access token using the refresh token."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user or not user.is_active:
        return jsonify({"error": "User not found or inactive"}), 401

    additional_claims = {"role": user.role, "villa_id": user.villa_id}
    new_access = create_access_token(identity=user_id, additional_claims=additional_claims)
    return jsonify({"access_token": new_access}), 200


@auth_bp.route("/logout", methods=["DELETE"])
@jwt_required()
def logout():
    """Revoke the current access token (add to blocklist)."""
    jti = get_jwt()["jti"]
    BLOCKLISTED_TOKENS.add(jti)
    return jsonify({"message": "Successfully logged out"}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict()), 200


@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    data = request.get_json()

    if not bcrypt.check_password_hash(user.password_hash, data.get("current_password", "")):
        return jsonify({"error": "Current password is incorrect"}), 400

    new_pw = data.get("new_password", "")
    if len(new_pw) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    user.password_hash = bcrypt.generate_password_hash(new_pw).decode("utf-8")
    db.session.commit()
    return jsonify({"message": "Password updated successfully"}), 200

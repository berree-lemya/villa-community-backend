from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db, bcrypt
from app.models import (
    User, Villa, Booking, MaintenanceRequest,
    GatePass, UserRole, MaintenanceStatus, BookingStatus, GatePassStatus
)
from app.utils import admin_required

admin_bp = Blueprint("admin", __name__)


# ── Dashboard Stats ─────────────────────────────────────────────────────────
@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
@admin_required
def dashboard_stats():
    stats = {
        "villas": {
            "total": Villa.query.count(),
            "occupied": Villa.query.filter_by(is_occupied=True).count(),
        },
        "users": {
            "total": User.query.count(),
            "owners": User.query.filter_by(role=UserRole.OWNER).count(),
            "tenants": User.query.filter_by(role=UserRole.TENANT).count(),
        },
        "bookings": {
            "total": Booking.query.count(),
            "confirmed": Booking.query.filter_by(status=BookingStatus.CONFIRMED).count(),
            "cancelled": Booking.query.filter_by(status=BookingStatus.CANCELLED).count(),
        },
        "maintenance": {
            "open": MaintenanceRequest.query.filter_by(status=MaintenanceStatus.OPEN).count(),
            "assigned": MaintenanceRequest.query.filter_by(status=MaintenanceStatus.ASSIGNED).count(),
            "in_progress": MaintenanceRequest.query.filter_by(status=MaintenanceStatus.IN_PROGRESS).count(),
            "resolved": MaintenanceRequest.query.filter_by(status=MaintenanceStatus.RESOLVED).count(),
        },
        "gate_passes": {
            "active": GatePass.query.filter_by(status=GatePassStatus.ACTIVE).count(),
            "total_today": GatePass.query.filter(
                db.func.date(GatePass.created_at) == db.func.current_date()
            ).count(),
        },
    }
    return jsonify(stats), 200


# ── User Management ─────────────────────────────────────────────────────────
@admin_bp.route("/users", methods=["GET"])
@jwt_required()
@admin_required
def list_users():
    role = request.args.get("role")
    q = User.query
    if role:
        q = q.filter_by(role=role)
    users = q.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@jwt_required()
@admin_required
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200


@admin_bp.route("/users", methods=["POST"])
@jwt_required()
@admin_required
def create_user():
    """Admin creates any role including admin/security."""
    data = request.get_json()
    required = ["name", "email", "password", "role"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Required: {required}"}), 400

    if User.query.filter_by(email=data["email"].lower()).first():
        return jsonify({"error": "Email already exists"}), 409

    hashed = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(
        name=data["name"],
        email=data["email"].lower(),
        phone=data.get("phone"),
        password_hash=hashed,
        role=data["role"],
        villa_id=data.get("villa_id"),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created", "user": user.to_dict()}), 201


@admin_bp.route("/users/<int:user_id>/deactivate", methods=["PUT"])
@jwt_required()
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    return jsonify({"message": f"User {user.name} deactivated"}), 200


@admin_bp.route("/users/<int:user_id>/activate", methods=["PUT"])
@jwt_required()
@admin_required
def activate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()
    return jsonify({"message": f"User {user.name} activated"}), 200


@admin_bp.route("/users/<int:user_id>/assign-villa", methods=["PUT"])
@jwt_required()
@admin_required
def assign_villa(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    villa_id = data.get("villa_id")

    if villa_id:
        villa = Villa.query.get(villa_id)
        if not villa:
            return jsonify({"error": "Villa not found"}), 404
        villa.is_occupied = True

    user.villa_id = villa_id
    db.session.commit()
    return jsonify({"message": "Villa assigned", "user": user.to_dict()}), 200

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models import (
    MaintenanceRequest, MaintenanceStatus, MaintenanceCategory,
    User, Notification
)
from app.utils import resident_required, admin_required

maintenance_bp = Blueprint("maintenance", __name__)

VALID_CATEGORIES = [
    MaintenanceCategory.ELECTRICIAN,
    MaintenanceCategory.PLUMBER,
    MaintenanceCategory.CARPENTER,
    MaintenanceCategory.OTHER,
]
VALID_PRIORITIES = ["low", "normal", "high", "urgent"]
VALID_TIME_SLOTS = ["morning", "afternoon", "evening"]


def _notify(user_id, title, message, notif_type="info", entity_id=None):
    n = Notification(
        user_id=user_id, title=title, message=message,
        notif_type=notif_type, related_entity="maintenance", related_id=entity_id
    )
    db.session.add(n)


# ── Create maintenance request ──────────────────────────────────────────────
@maintenance_bp.route("/", methods=["POST"])
@jwt_required()
@resident_required
def create_request():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user.villa_id:
        return jsonify({"error": "You are not assigned to a villa"}), 400

    data = request.get_json()
    required = ["category", "title", "description"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Required fields: {required}"}), 400

    if data["category"] not in VALID_CATEGORIES:
        return jsonify({"error": f"Category must be one of {VALID_CATEGORIES}"}), 400

    priority = data.get("priority", "normal")
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": f"Priority must be one of {VALID_PRIORITIES}"}), 400

    req = MaintenanceRequest(
        user_id=user_id,
        villa_id=user.villa_id,
        category=data["category"],
        title=data["title"].strip(),
        description=data["description"].strip(),
        priority=priority,
        preferred_date=datetime.strptime(data["preferred_date"], "%Y-%m-%d").date()
            if data.get("preferred_date") else None,
        preferred_time_slot=data.get("preferred_time_slot"),
        status=MaintenanceStatus.OPEN,
    )
    db.session.add(req)
    db.session.flush()

    _notify(
        user_id,
        title="Maintenance Request Submitted",
        message=f"Your {data['category']} request has been received. We'll schedule it soon.",
        notif_type="info",
        entity_id=req.id,
    )
    db.session.commit()
    return jsonify({"message": "Maintenance request submitted", "request": req.to_dict()}), 201


# ── My maintenance requests ─────────────────────────────────────────────────
@maintenance_bp.route("/my", methods=["GET"])
@jwt_required()
def my_requests():
    user_id = int(get_jwt_identity())
    status = request.args.get("status")
    category = request.args.get("category")

    q = MaintenanceRequest.query.filter_by(user_id=user_id)
    if status:
        q = q.filter_by(status=status)
    if category:
        q = q.filter_by(category=category)

    requests = q.order_by(MaintenanceRequest.created_at.desc()).all()
    return jsonify([r.to_dict() for r in requests]), 200


# ── Get single request ──────────────────────────────────────────────────────
@maintenance_bp.route("/<int:req_id>", methods=["GET"])
@jwt_required()
def get_request(req_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    req = MaintenanceRequest.query.get_or_404(req_id)

    if req.user_id != user_id and claims.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    return jsonify(req.to_dict()), 200


# ── Update request (resident can update if still OPEN) ─────────────────────
@maintenance_bp.route("/<int:req_id>", methods=["PUT"])
@jwt_required()
def update_request(req_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    req = MaintenanceRequest.query.get_or_404(req_id)

    if req.user_id != user_id and claims.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    if req.status not in [MaintenanceStatus.OPEN] and claims.get("role") != "admin":
        return jsonify({"error": "Cannot edit a request that is already assigned or resolved"}), 400

    data = request.get_json()
    for field in ["title", "description", "priority", "preferred_time_slot"]:
        if field in data:
            setattr(req, field, data[field])

    if "preferred_date" in data and data["preferred_date"]:
        req.preferred_date = datetime.strptime(data["preferred_date"], "%Y-%m-%d").date()

    db.session.commit()
    return jsonify({"message": "Request updated", "request": req.to_dict()}), 200


# ── Cancel request ──────────────────────────────────────────────────────────
@maintenance_bp.route("/<int:req_id>/cancel", methods=["PUT"])
@jwt_required()
def cancel_request(req_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    req = MaintenanceRequest.query.get_or_404(req_id)

    if req.user_id != user_id and claims.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    if req.status in [MaintenanceStatus.RESOLVED, MaintenanceStatus.CLOSED]:
        return jsonify({"error": "Cannot cancel a completed request"}), 400

    req.status = MaintenanceStatus.CLOSED
    _notify(req.user_id, "Maintenance Request Cancelled",
            f"Your {req.category} request '{req.title}' has been cancelled.",
            notif_type="warning", entity_id=req_id)
    db.session.commit()
    return jsonify({"message": "Request cancelled"}), 200


# ── Rate a completed request ────────────────────────────────────────────────
@maintenance_bp.route("/<int:req_id>/rate", methods=["PUT"])
@jwt_required()
def rate_request(req_id):
    user_id = int(get_jwt_identity())
    req = MaintenanceRequest.query.get_or_404(req_id)

    if req.user_id != user_id:
        return jsonify({"error": "Access denied"}), 403

    if req.status != MaintenanceStatus.RESOLVED:
        return jsonify({"error": "Can only rate resolved requests"}), 400

    data = request.get_json()
    rating = data.get("rating")
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400

    req.rating = rating
    db.session.commit()
    return jsonify({"message": "Thank you for your feedback!"}), 200


# ── ADMIN: list all requests ────────────────────────────────────────────────
@maintenance_bp.route("/all", methods=["GET"])
@jwt_required()
@admin_required
def all_requests():
    status = request.args.get("status")
    category = request.args.get("category")
    priority = request.args.get("priority")

    q = MaintenanceRequest.query
    if status:
        q = q.filter_by(status=status)
    if category:
        q = q.filter_by(category=category)
    if priority:
        q = q.filter_by(priority=priority)

    requests = q.order_by(
        MaintenanceRequest.priority.desc(),
        MaintenanceRequest.created_at.asc()
    ).all()
    return jsonify([r.to_dict() for r in requests]), 200


# ── ADMIN: assign technician ────────────────────────────────────────────────
@maintenance_bp.route("/<int:req_id>/assign", methods=["PUT"])
@jwt_required()
@admin_required
def assign_request(req_id):
    req = MaintenanceRequest.query.get_or_404(req_id)
    data = request.get_json()

    assigned_to = data.get("assigned_to", "").strip()
    if not assigned_to:
        return jsonify({"error": "technician name required"}), 400

    req.assigned_to = assigned_to
    req.assigned_at = datetime.utcnow()
    req.status = MaintenanceStatus.ASSIGNED

    _notify(
        req.user_id,
        title="Technician Assigned",
        message=f"A technician ({assigned_to}) has been assigned to your {req.category} request.",
        notif_type="success",
        entity_id=req_id,
    )
    db.session.commit()
    return jsonify({"message": "Technician assigned", "request": req.to_dict()}), 200


# ── ADMIN: resolve request ──────────────────────────────────────────────────
@maintenance_bp.route("/<int:req_id>/resolve", methods=["PUT"])
@jwt_required()
@admin_required
def resolve_request(req_id):
    req = MaintenanceRequest.query.get_or_404(req_id)
    data = request.get_json() or {}

    req.status = MaintenanceStatus.RESOLVED
    req.resolved_at = datetime.utcnow()
    req.resolution_notes = data.get("resolution_notes", "Issue resolved.")

    _notify(
        req.user_id,
        title="Maintenance Request Resolved",
        message=f"Your {req.category} request has been resolved. Please rate the service.",
        notif_type="success",
        entity_id=req_id,
    )
    db.session.commit()
    return jsonify({"message": "Request marked as resolved", "request": req.to_dict()}), 200

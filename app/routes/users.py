from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Notification

users_bp = Blueprint("users", __name__)


@users_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200


@users_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    for field in ["name", "phone", "profile_picture"]:
        if field in data:
            setattr(user, field, data[field])

    db.session.commit()
    return jsonify({"message": "Profile updated", "user": user.to_dict()}), 200


# ── Notifications ───────────────────────────────────────────────────────────
@users_bp.route("/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    user_id = int(get_jwt_identity())
    unread_only = request.args.get("unread", "false").lower() == "true"

    q = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        q = q.filter_by(is_read=False)

    notifications = q.order_by(Notification.created_at.desc()).limit(50).all()
    return jsonify([n.to_dict() for n in notifications]), 200


@users_bp.route("/notifications/<int:notif_id>/read", methods=["PUT"])
@jwt_required()
def mark_read(notif_id):
    user_id = int(get_jwt_identity())
    notif = Notification.query.get_or_404(notif_id)

    if notif.user_id != user_id:
        return jsonify({"error": "Access denied"}), 403

    notif.is_read = True
    db.session.commit()
    return jsonify({"message": "Marked as read"}), 200


@users_bp.route("/notifications/read-all", methods=["PUT"])
@jwt_required()
def mark_all_read():
    user_id = int(get_jwt_identity())
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"}), 200

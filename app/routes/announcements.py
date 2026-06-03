from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Announcement, User
from app.utils import admin_required

announcements_bp = Blueprint("announcements", __name__)

@announcements_bp.route("/", methods=["GET"])
@jwt_required()
def list_announcements():
    pinned = Announcement.query.filter_by(is_active=True, pinned=True).order_by(Announcement.created_at.desc()).all()
    regular = Announcement.query.filter_by(is_active=True, pinned=False).order_by(Announcement.created_at.desc()).limit(50).all()
    return jsonify({"pinned": [a.to_dict() for a in pinned], "announcements": [a.to_dict() for a in regular]}), 200

@announcements_bp.route("/<int:ann_id>", methods=["GET"])
@jwt_required()
def get_announcement(ann_id):
    a = Announcement.query.get_or_404(ann_id)
    return jsonify(a.to_dict()), 200

@announcements_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_announcement():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data.get("title") or not data.get("body"):
        return jsonify({"error": "title and body are required"}), 400
    expires = None
    if data.get("expires_at"):
        try:
            expires = datetime.fromisoformat(data["expires_at"])
        except ValueError:
            return jsonify({"error": "expires_at must be ISO datetime"}), 400
    ann = Announcement(
        title=data["title"].strip(),
        body=data["body"].strip(),
        priority=data.get("priority", "normal"),
        category=data.get("category", "general"),
        posted_by=user_id,
        pinned=data.get("pinned", False),
        expires_at=expires,
    )
    db.session.add(ann)
    db.session.commit()
    return jsonify({"message": "Announcement posted", "announcement": ann.to_dict()}), 201

@announcements_bp.route("/<int:ann_id>", methods=["PUT"])
@jwt_required()
@admin_required
def update_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    data = request.get_json()
    for field in ["title", "body", "priority", "category", "pinned", "is_active"]:
        if field in data:
            setattr(ann, field, data[field])
    db.session.commit()
    return jsonify({"message": "Updated", "announcement": ann.to_dict()}), 200

@announcements_bp.route("/<int:ann_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    ann.is_active = False
    db.session.commit()
    return jsonify({"message": "Announcement removed"}), 200

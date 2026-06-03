from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Villa
from app.utils import admin_required

villas_bp = Blueprint("villas", __name__)


@villas_bp.route("/", methods=["GET"])
@jwt_required()
def list_villas():
    villas = Villa.query.order_by(Villa.villa_number).all()
    return jsonify([v.to_dict() for v in villas]), 200


@villas_bp.route("/<int:villa_id>", methods=["GET"])
@jwt_required()
def get_villa(villa_id):
    villa = Villa.query.get_or_404(villa_id)
    return jsonify(villa.to_dict()), 200


@villas_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_villa():
    data = request.get_json()
    if not data.get("villa_number"):
        return jsonify({"error": "villa_number is required"}), 400

    if Villa.query.filter_by(villa_number=data["villa_number"]).first():
        return jsonify({"error": "Villa number already exists"}), 409

    villa = Villa(
        villa_number=data["villa_number"],
        block=data.get("block"),
        floor=data.get("floor", 0),
        bedrooms=data.get("bedrooms", 3),
        area_sqft=data.get("area_sqft"),
    )
    db.session.add(villa)
    db.session.commit()
    return jsonify({"message": "Villa created", "villa": villa.to_dict()}), 201

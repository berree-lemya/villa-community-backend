from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models import ParkingSlot, ParkingStatus, User, Villa
from app.utils import admin_required

parking_bp = Blueprint("parking", __name__)

@parking_bp.route("/", methods=["GET"])
@jwt_required()
def list_slots():
    slot_type = request.args.get("type")
    status = request.args.get("status")
    q = ParkingSlot.query
    if slot_type:
        q = q.filter_by(slot_type=slot_type)
    if status:
        q = q.filter_by(status=status)
    slots = q.order_by(ParkingSlot.slot_number).all()
    return jsonify([s.to_dict() for s in slots]), 200

@parking_bp.route("/my", methods=["GET"])
@jwt_required()
def my_slots():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user.villa_id:
        return jsonify([]), 200
    slots = ParkingSlot.query.filter_by(assigned_villa_id=user.villa_id).all()
    return jsonify([s.to_dict() for s in slots]), 200

@parking_bp.route("/summary", methods=["GET"])
@jwt_required()
def summary():
    total = ParkingSlot.query.count()
    available = ParkingSlot.query.filter_by(status=ParkingStatus.AVAILABLE).count()
    occupied = ParkingSlot.query.filter_by(status=ParkingStatus.OCCUPIED).count()
    return jsonify({"total": total, "available": available, "occupied": occupied,
                    "visitor_available": ParkingSlot.query.filter_by(slot_type="visitor", status=ParkingStatus.AVAILABLE).count()}), 200

@parking_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_slot():
    data = request.get_json()
    if not data.get("slot_number"):
        return jsonify({"error": "slot_number required"}), 400
    if ParkingSlot.query.filter_by(slot_number=data["slot_number"]).first():
        return jsonify({"error": "Slot number already exists"}), 409
    slot = ParkingSlot(
        slot_number=data["slot_number"],
        block=data.get("block"),
        slot_type=data.get("slot_type", "car"),
        status=ParkingStatus.AVAILABLE,
    )
    db.session.add(slot)
    db.session.commit()
    return jsonify({"message": "Slot created", "slot": slot.to_dict()}), 201

@parking_bp.route("/<int:slot_id>/assign", methods=["PUT"])
@jwt_required()
@admin_required
def assign_slot(slot_id):
    slot = ParkingSlot.query.get_or_404(slot_id)
    data = request.get_json()
    villa_id = data.get("villa_id")
    if villa_id and not Villa.query.get(villa_id):
        return jsonify({"error": "Villa not found"}), 404
    slot.assigned_villa_id = villa_id
    slot.vehicle_number = data.get("vehicle_number")
    slot.vehicle_type = data.get("vehicle_type")
    slot.notes = data.get("notes")
    slot.status = ParkingStatus.OCCUPIED if villa_id else ParkingStatus.AVAILABLE
    db.session.commit()
    return jsonify({"message": "Slot updated", "slot": slot.to_dict()}), 200

@parking_bp.route("/<int:slot_id>/status", methods=["PUT"])
@jwt_required()
@admin_required
def update_status(slot_id):
    slot = ParkingSlot.query.get_or_404(slot_id)
    data = request.get_json()
    valid = [ParkingStatus.AVAILABLE, ParkingStatus.OCCUPIED, ParkingStatus.RESERVED, ParkingStatus.MAINTENANCE]
    if data.get("status") not in valid:
        return jsonify({"error": f"status must be one of {valid}"}), 400
    slot.status = data["status"]
    db.session.commit()
    return jsonify({"message": "Status updated", "slot": slot.to_dict()}), 200

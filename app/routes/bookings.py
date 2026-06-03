from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models import Booking, Amenity, User, BookingStatus, Notification
from app.utils import resident_required, admin_required

bookings_bp = Blueprint("bookings", __name__)


def _notify(user_id, title, message, notif_type="info", entity="booking", entity_id=None):
    n = Notification(
        user_id=user_id, title=title, message=message,
        notif_type=notif_type, related_entity=entity, related_id=entity_id
    )
    db.session.add(n)


# ── List all amenities ──────────────────────────────────────────────────────
@bookings_bp.route("/amenities", methods=["GET"])
@jwt_required()
def list_amenities():
    amenities = Amenity.query.filter_by(is_active=True).all()
    return jsonify([a.to_dict() for a in amenities]), 200


# ── Check availability for an amenity on a date ────────────────────────────
@bookings_bp.route("/amenities/<int:amenity_id>/availability", methods=["GET"])
@jwt_required()
def check_availability(amenity_id):
    """
    Returns all booked slots for an amenity on a given date.
    Query param: ?date=YYYY-MM-DD
    """
    amenity = Amenity.query.get_or_404(amenity_id)
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Query param 'date' is required (YYYY-MM-DD)"}), 400

    try:
        query_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    bookings = Booking.query.filter_by(
        amenity_id=amenity_id,
        booking_date=query_date,
    ).filter(Booking.status != BookingStatus.CANCELLED).all()

    booked_slots = [{"start": b.start_time, "end": b.end_time} for b in bookings]

    return jsonify({
        "amenity": amenity.to_dict(),
        "date": date_str,
        "booked_slots": booked_slots,
        "capacity": amenity.capacity,
        "slot_duration_minutes": amenity.slot_duration_minutes,
    }), 200


# ── Create a booking ────────────────────────────────────────────────────────
@bookings_bp.route("/", methods=["POST"])
@jwt_required()
@resident_required
def create_booking():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    required = ["amenity_id", "booking_date", "start_time", "end_time"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Required fields: {required}"}), 400

    amenity = Amenity.query.get(data["amenity_id"])
    if not amenity or not amenity.is_active:
        return jsonify({"error": "Amenity not found or unavailable"}), 404

    try:
        booking_date = date.fromisoformat(data["booking_date"])
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if booking_date < date.today():
        return jsonify({"error": "Cannot book for a past date"}), 400

    start = data["start_time"]
    end = data["end_time"]

    # Validate against open/close hours
    if start < amenity.open_time or end > amenity.close_time:
        return jsonify({
            "error": f"Bookings allowed only between {amenity.open_time} and {amenity.close_time}"
        }), 400

    # Check capacity: count overlapping confirmed bookings
    overlapping = Booking.query.filter(
        Booking.amenity_id == data["amenity_id"],
        Booking.booking_date == booking_date,
        Booking.status != BookingStatus.CANCELLED,
        Booking.start_time < end,
        Booking.end_time > start,
    ).count()

    if overlapping >= amenity.capacity:
        return jsonify({"error": "This slot is fully booked. Please choose another time."}), 409

    booking = Booking(
        user_id=user_id,
        amenity_id=data["amenity_id"],
        booking_date=booking_date,
        start_time=start,
        end_time=end,
        num_guests=data.get("num_guests", 1),
        notes=data.get("notes"),
        status=BookingStatus.CONFIRMED,
    )
    db.session.add(booking)
    db.session.flush()  # get booking.id before commit

    _notify(
        user_id,
        title=f"Booking Confirmed – {amenity.name}",
        message=f"Your booking for {amenity.name} on {booking_date} ({start}–{end}) is confirmed.",
        notif_type="success",
        entity_id=booking.id,
    )
    db.session.commit()
    return jsonify({"message": "Booking created", "booking": booking.to_dict()}), 201


# ── List my bookings ────────────────────────────────────────────────────────
@bookings_bp.route("/my", methods=["GET"])
@jwt_required()
def my_bookings():
    user_id = int(get_jwt_identity())
    status_filter = request.args.get("status")

    q = Booking.query.filter_by(user_id=user_id)
    if status_filter:
        q = q.filter_by(status=status_filter)

    bookings = q.order_by(Booking.booking_date.desc()).all()
    return jsonify([b.to_dict() for b in bookings]), 200


# ── Get a single booking ────────────────────────────────────────────────────
@bookings_bp.route("/<int:booking_id>", methods=["GET"])
@jwt_required()
def get_booking(booking_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != user_id and claims.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    return jsonify(booking.to_dict()), 200


# ── Cancel a booking ────────────────────────────────────────────────────────
@bookings_bp.route("/<int:booking_id>/cancel", methods=["PUT"])
@jwt_required()
def cancel_booking(booking_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != user_id and claims.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    if booking.status == BookingStatus.CANCELLED:
        return jsonify({"error": "Booking is already cancelled"}), 400

    data = request.get_json() or {}
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = datetime.utcnow()
    booking.cancel_reason = data.get("reason", "Cancelled by user")

    _notify(
        booking.user_id,
        title="Booking Cancelled",
        message=f"Your {booking.amenity.name} booking on {booking.booking_date} has been cancelled.",
        notif_type="warning",
        entity_id=booking_id,
    )
    db.session.commit()
    return jsonify({"message": "Booking cancelled", "booking": booking.to_dict()}), 200


# ── Admin: list all bookings ────────────────────────────────────────────────
@bookings_bp.route("/all", methods=["GET"])
@jwt_required()
@admin_required
def all_bookings():
    amenity_id = request.args.get("amenity_id", type=int)
    status = request.args.get("status")
    date_str = request.args.get("date")

    q = Booking.query
    if amenity_id:
        q = q.filter_by(amenity_id=amenity_id)
    if status:
        q = q.filter_by(status=status)
    if date_str:
        try:
            q = q.filter_by(booking_date=date.fromisoformat(date_str))
        except ValueError:
            pass

    bookings = q.order_by(Booking.booking_date.desc()).all()
    return jsonify([b.to_dict() for b in bookings]), 200

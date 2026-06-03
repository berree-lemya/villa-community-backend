import random
import string
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models import GatePass, GatePassStatus, GatePassType, User, Notification
from app.utils import resident_required, security_required, admin_required

gate_bp = Blueprint("gate", __name__)

VALID_PASS_TYPES = [
    GatePassType.VISITOR,
    GatePassType.MAID,
    GatePassType.DELIVERY,
    GatePassType.CONTRACTOR,
]


def _generate_pass_code():
    """Generate a unique 8-char alphanumeric pass code like GP-A1B2C3."""
    while True:
        code = "GP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not GatePass.query.filter_by(pass_code=code).first():
            return code


def _notify(user_id, title, message, notif_type="info", entity_id=None):
    n = Notification(
        user_id=user_id, title=title, message=message,
        notif_type=notif_type, related_entity="gate", related_id=entity_id
    )
    db.session.add(n)


# ── Create gate pass ────────────────────────────────────────────────────────
@gate_bp.route("/", methods=["POST"])
@jwt_required()
@resident_required
def create_gate_pass():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user.villa_id:
        return jsonify({"error": "You are not assigned to a villa"}), 400

    data = request.get_json()
    required = ["pass_type", "visitor_name", "valid_from", "valid_until"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Required fields: {required}"}), 400

    if data["pass_type"] not in VALID_PASS_TYPES:
        return jsonify({"error": f"pass_type must be one of {VALID_PASS_TYPES}"}), 400

    try:
        valid_from = datetime.fromisoformat(data["valid_from"])
        valid_until = datetime.fromisoformat(data["valid_until"])
    except ValueError:
        return jsonify({"error": "Datetime format must be ISO 8601: YYYY-MM-DDTHH:MM:SS"}), 400

    if valid_until <= valid_from:
        return jsonify({"error": "valid_until must be after valid_from"}), 400

    gate_pass = GatePass(
        pass_code=_generate_pass_code(),
        villa_id=user.villa_id,
        requested_by=user_id,
        pass_type=data["pass_type"],
        visitor_name=data["visitor_name"].strip(),
        visitor_phone=data.get("visitor_phone"),
        visitor_vehicle=data.get("visitor_vehicle"),
        purpose=data.get("purpose"),
        valid_from=valid_from,
        valid_until=valid_until,
        is_recurring=data.get("is_recurring", False),
        recurring_days=data.get("recurring_days"),  # "Mon,Wed,Fri"
        status=GatePassStatus.ACTIVE,
    )
    db.session.add(gate_pass)
    db.session.flush()

    _notify(
        user_id,
        title="Gate Pass Created",
        message=f"Pass code {gate_pass.pass_code} created for {gate_pass.visitor_name}.",
        notif_type="success",
        entity_id=gate_pass.id,
    )
    db.session.commit()
    return jsonify({"message": "Gate pass created", "gate_pass": gate_pass.to_dict()}), 201


# ── My gate passes ──────────────────────────────────────────────────────────
@gate_bp.route("/my", methods=["GET"])
@jwt_required()
def my_gate_passes():
    user_id = int(get_jwt_identity())
    status = request.args.get("status")
    pass_type = request.args.get("pass_type")

    q = GatePass.query.filter_by(requested_by=user_id)
    if status:
        q = q.filter_by(status=status)
    if pass_type:
        q = q.filter_by(pass_type=pass_type)

    passes = q.order_by(GatePass.created_at.desc()).all()
    return jsonify([p.to_dict() for p in passes]), 200


# ── Get single gate pass ────────────────────────────────────────────────────
@gate_bp.route("/<int:pass_id>", methods=["GET"])
@jwt_required()
def get_gate_pass(pass_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    gp = GatePass.query.get_or_404(pass_id)

    allowed_roles = ["admin", "security"]
    if gp.requested_by != user_id and claims.get("role") not in allowed_roles:
        return jsonify({"error": "Access denied"}), 403

    return jsonify(gp.to_dict()), 200


# ── Revoke a gate pass (resident can revoke their own) ──────────────────────
@gate_bp.route("/<int:pass_id>/revoke", methods=["PUT"])
@jwt_required()
def revoke_gate_pass(pass_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    gp = GatePass.query.get_or_404(pass_id)

    allowed_roles = ["admin", "security"]
    if gp.requested_by != user_id and claims.get("role") not in allowed_roles:
        return jsonify({"error": "Access denied"}), 403

    if gp.status != GatePassStatus.ACTIVE:
        return jsonify({"error": "Gate pass is not active"}), 400

    gp.status = GatePassStatus.REVOKED
    _notify(
        gp.requested_by,
        title="Gate Pass Revoked",
        message=f"Gate pass {gp.pass_code} for {gp.visitor_name} has been revoked.",
        notif_type="warning",
        entity_id=pass_id,
    )
    db.session.commit()
    return jsonify({"message": "Gate pass revoked"}), 200


# ── SECURITY: verify pass code at gate ─────────────────────────────────────
@gate_bp.route("/verify/<string:pass_code>", methods=["GET"])
@jwt_required()
@security_required
def verify_pass(pass_code):
    """Security guard scans/enters the pass code at the gate."""
    gp = GatePass.query.filter_by(pass_code=pass_code.upper()).first()
    if not gp:
        return jsonify({"valid": False, "error": "Pass code not found"}), 404

    now = datetime.utcnow()

    if gp.status == GatePassStatus.REVOKED:
        return jsonify({"valid": False, "error": "Pass has been revoked by resident"}), 403

    if gp.status == GatePassStatus.EXPIRED or now > gp.valid_until:
        gp.status = GatePassStatus.EXPIRED
        db.session.commit()
        return jsonify({"valid": False, "error": "Pass has expired"}), 403

    if now < gp.valid_from:
        return jsonify({"valid": False, "error": "Pass is not yet valid"}), 403

    return jsonify({
        "valid": True,
        "gate_pass": gp.to_dict(),
    }), 200


# ── SECURITY: check in visitor ──────────────────────────────────────────────
@gate_bp.route("/<int:pass_id>/checkin", methods=["PUT"])
@jwt_required()
@security_required
def check_in(pass_id):
    gp = GatePass.query.get_or_404(pass_id)
    now = datetime.utcnow()

    if gp.status != GatePassStatus.ACTIVE:
        return jsonify({"error": f"Pass is not active (status: {gp.status})"}), 400

    if now > gp.valid_until or now < gp.valid_from:
        return jsonify({"error": "Pass is outside its validity window"}), 400

    data = request.get_json() or {}
    gp.checked_in_at = now
    gp.security_notes = data.get("notes")

    if not gp.is_recurring:
        gp.status = GatePassStatus.USED

    _notify(
        gp.requested_by,
        title="Visitor Arrived",
        message=f"{gp.visitor_name} has entered the community (Villa {gp.villa.villa_number}).",
        notif_type="info",
        entity_id=pass_id,
    )
    db.session.commit()
    return jsonify({"message": "Visitor checked in", "gate_pass": gp.to_dict()}), 200


# ── SECURITY: check out visitor ─────────────────────────────────────────────
@gate_bp.route("/<int:pass_id>/checkout", methods=["PUT"])
@jwt_required()
@security_required
def check_out(pass_id):
    gp = GatePass.query.get_or_404(pass_id)

    if not gp.checked_in_at:
        return jsonify({"error": "Visitor has not checked in yet"}), 400

    gp.checked_out_at = datetime.utcnow()

    _notify(
        gp.requested_by,
        title="Visitor Departed",
        message=f"{gp.visitor_name} has left the community.",
        notif_type="info",
        entity_id=pass_id,
    )
    db.session.commit()
    return jsonify({"message": "Visitor checked out", "gate_pass": gp.to_dict()}), 200


# ── SECURITY/ADMIN: all active passes ──────────────────────────────────────
@gate_bp.route("/active", methods=["GET"])
@jwt_required()
@security_required
def active_passes():
    now = datetime.utcnow()
    passes = GatePass.query.filter(
        GatePass.status == GatePassStatus.ACTIVE,
        GatePass.valid_until >= now,
    ).order_by(GatePass.valid_from.asc()).all()
    return jsonify([p.to_dict() for p in passes]), 200


# ── ADMIN: all passes with filters ─────────────────────────────────────────
@gate_bp.route("/all", methods=["GET"])
@jwt_required()
@admin_required
def all_passes():
    status = request.args.get("status")
    pass_type = request.args.get("pass_type")
    villa_id = request.args.get("villa_id", type=int)

    q = GatePass.query
    if status:
        q = q.filter_by(status=status)
    if pass_type:
        q = q.filter_by(pass_type=pass_type)
    if villa_id:
        q = q.filter_by(villa_id=villa_id)

    passes = q.order_by(GatePass.created_at.desc()).all()
    return jsonify([p.to_dict() for p in passes]), 200

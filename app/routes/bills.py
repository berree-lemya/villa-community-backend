from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models import Bill, BillStatus, BillCategory, User, Notification, Villa
from app.utils import resident_required, admin_required

bills_bp = Blueprint("bills", __name__)

def _notify(user_id, title, message, notif_type="info", entity_id=None):
    n = Notification(user_id=user_id, title=title, message=message,
                     notif_type=notif_type, related_entity="bill", related_id=entity_id)
    db.session.add(n)

@bills_bp.route("/my", methods=["GET"])
@jwt_required()
def my_bills():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user.villa_id:
        return jsonify([]), 200
    status = request.args.get("status")
    q = Bill.query.filter_by(villa_id=user.villa_id)
    if status:
        q = q.filter_by(status=status)
    today = date.today()
    for bill in q.all():
        if bill.status == BillStatus.UNPAID and bill.due_date < today:
            bill.status = BillStatus.OVERDUE
    db.session.commit()
    bills = q.order_by(Bill.due_date.asc()).all()
    return jsonify([b.to_dict() for b in bills]), 200

@bills_bp.route("/summary", methods=["GET"])
@jwt_required()
def bill_summary():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user.villa_id:
        return jsonify({"total_due": 0, "overdue": 0, "paid_total": 0, "unpaid_count": 0, "overdue_count": 0}), 200
    bills = Bill.query.filter_by(villa_id=user.villa_id).all()
    return jsonify({
        "total_due": sum(b.amount for b in bills if b.status in [BillStatus.UNPAID, BillStatus.OVERDUE]),
        "overdue": sum(b.amount for b in bills if b.status == BillStatus.OVERDUE),
        "paid_total": sum(b.amount for b in bills if b.status == BillStatus.PAID),
        "unpaid_count": sum(1 for b in bills if b.status == BillStatus.UNPAID),
        "overdue_count": sum(1 for b in bills if b.status == BillStatus.OVERDUE),
    }), 200

@bills_bp.route("/<int:bill_id>/pay", methods=["PUT"])
@jwt_required()
def pay_bill(bill_id):
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    bill = Bill.query.get_or_404(bill_id)
    if bill.villa_id != user.villa_id:
        return jsonify({"error": "Access denied"}), 403
    if bill.status == BillStatus.PAID:
        return jsonify({"error": "Bill already paid"}), 400
    data = request.get_json() or {}
    bill.status = BillStatus.PAID
    bill.paid_at = datetime.utcnow()
    bill.payment_method = data.get("payment_method", "online")
    bill.transaction_ref = data.get("transaction_ref", f"TXN{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    _notify(user_id, "Payment Successful",
            f"Rs.{bill.amount:.0f} paid for '{bill.title}'. Ref: {bill.transaction_ref}",
            notif_type="success", entity_id=bill_id)
    db.session.commit()
    return jsonify({"message": "Payment recorded", "bill": bill.to_dict()}), 200

@bills_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_bill():
    data = request.get_json()
    required = ["villa_id", "title", "category", "amount", "due_date"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Required: {required}"}), 400
    villa = Villa.query.get(data["villa_id"])
    if not villa:
        return jsonify({"error": "Villa not found"}), 404
    try:
        due = date.fromisoformat(data["due_date"])
    except ValueError:
        return jsonify({"error": "due_date must be YYYY-MM-DD"}), 400
    bill = Bill(villa_id=data["villa_id"], title=data["title"], category=data["category"],
                amount=float(data["amount"]), due_date=due, description=data.get("description"),
                status=BillStatus.UNPAID)
    db.session.add(bill)
    db.session.flush()
    for user in villa.users:
        _notify(user.id, "New Bill Generated",
                f"A new bill '{bill.title}' of Rs.{bill.amount:.0f} is due by {due}.",
                notif_type="warning", entity_id=bill.id)
    db.session.commit()
    return jsonify({"message": "Bill created", "bill": bill.to_dict()}), 201

@bills_bp.route("/bulk", methods=["POST"])
@jwt_required()
@admin_required
def create_bulk_bills():
    data = request.get_json()
    required = ["title", "category", "amount", "due_date"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Required: {required}"}), 400
    try:
        due = date.fromisoformat(data["due_date"])
    except ValueError:
        return jsonify({"error": "due_date must be YYYY-MM-DD"}), 400
    villas = Villa.query.filter_by(is_occupied=True).all()
    count = 0
    for villa in villas:
        bill = Bill(villa_id=villa.id, title=data["title"], category=data["category"],
                    amount=float(data["amount"]), due_date=due,
                    description=data.get("description"), status=BillStatus.UNPAID)
        db.session.add(bill)
        db.session.flush()
        for user in villa.users:
            _notify(user.id, "New Bill Generated",
                    f"'{bill.title}' of Rs.{bill.amount:.0f} due by {due}.",
                    notif_type="warning", entity_id=bill.id)
        count += 1
    db.session.commit()
    return jsonify({"message": f"Bills created for {count} occupied villas"}), 201

@bills_bp.route("/all", methods=["GET"])
@jwt_required()
@admin_required
def all_bills():
    status = request.args.get("status")
    villa_id = request.args.get("villa_id", type=int)
    q = Bill.query
    if status:
        q = q.filter_by(status=status)
    if villa_id:
        q = q.filter_by(villa_id=villa_id)
    bills = q.order_by(Bill.due_date.asc()).all()
    return jsonify([b.to_dict() for b in bills]), 200

@bills_bp.route("/<int:bill_id>/waive", methods=["PUT"])
@jwt_required()
@admin_required
def waive_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    bill.status = BillStatus.WAIVED
    db.session.commit()
    return jsonify({"message": "Bill waived", "bill": bill.to_dict()}), 200

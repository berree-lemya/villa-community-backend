from datetime import datetime, date
from app import db


class UserRole:
    OWNER = "owner"
    TENANT = "tenant"
    ADMIN = "admin"
    SECURITY = "security"

class BookingStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class MaintenanceStatus:
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class MaintenanceCategory:
    ELECTRICIAN = "electrician"
    PLUMBER = "plumber"
    CARPENTER = "carpenter"
    OTHER = "other"

class AmenityType:
    TENNIS_COURT = "tennis_court"
    SWIMMING_POOL = "swimming_pool"
    CLUBHOUSE = "clubhouse"
    GYM = "gym"

class GatePassType:
    VISITOR = "visitor"
    MAID = "maid"
    DELIVERY = "delivery"
    CONTRACTOR = "contractor"

class GatePassStatus:
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"

class ParkingStatus:
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"

class BillStatus:
    UNPAID = "unpaid"
    PAID = "paid"
    OVERDUE = "overdue"
    WAIVED = "waived"

class BillCategory:
    MAINTENANCE = "maintenance"
    AMENITY = "amenity"
    PARKING = "parking"
    WATER = "water"
    ELECTRICITY = "electricity"
    OTHER = "other"

class AnnouncementPriority:
    NORMAL = "normal"
    IMPORTANT = "important"
    URGENT = "urgent"


# ── VILLA ──────────────────────────────────────
class Villa(db.Model):
    __tablename__ = "villas"
    id = db.Column(db.Integer, primary_key=True)
    villa_number = db.Column(db.String(10), unique=True, nullable=False)
    block = db.Column(db.String(10), nullable=True)
    floor = db.Column(db.Integer, default=0)
    bedrooms = db.Column(db.Integer, default=3)
    area_sqft = db.Column(db.Float, nullable=True)
    is_occupied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("User", backref="villa", lazy=True)
    maintenance_requests = db.relationship("MaintenanceRequest", backref="villa", lazy=True)
    gate_passes = db.relationship("GatePass", backref="villa", lazy=True)

    def to_dict(self):
        return {"id": self.id, "villa_number": self.villa_number, "block": self.block,
                "floor": self.floor, "bedrooms": self.bedrooms, "area_sqft": self.area_sqft,
                "is_occupied": self.is_occupied}


# ── USER ───────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default=UserRole.TENANT, nullable=False)
    villa_id = db.Column(db.Integer, db.ForeignKey("villas.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    profile_picture = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    bookings = db.relationship("Booking", backref="user", lazy=True)
    maintenance_requests = db.relationship("MaintenanceRequest", backref="user", lazy=True)
    gate_passes = db.relationship("GatePass", backref="requested_by_user", lazy=True, foreign_keys="GatePass.requested_by")
    notifications = db.relationship("Notification", backref="user", lazy=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "phone": self.phone,
                "role": self.role, "villa_id": self.villa_id,
                "villa_number": self.villa.villa_number if self.villa else None,
                "is_active": self.is_active, "created_at": self.created_at.isoformat()}


# ── AMENITY ────────────────────────────────────
class Amenity(db.Model):
    __tablename__ = "amenities"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amenity_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    capacity = db.Column(db.Integer, default=10)
    slot_duration_minutes = db.Column(db.Integer, default=60)
    open_time = db.Column(db.String(10), default="06:00")
    close_time = db.Column(db.String(10), default="22:00")
    is_active = db.Column(db.Boolean, default=True)
    rules = db.Column(db.Text, nullable=True)
    bookings = db.relationship("Booking", backref="amenity", lazy=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "amenity_type": self.amenity_type,
                "description": self.description, "capacity": self.capacity,
                "slot_duration_minutes": self.slot_duration_minutes,
                "open_time": self.open_time, "close_time": self.close_time,
                "is_active": self.is_active}


# ── BOOKING ────────────────────────────────────
class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amenity_id = db.Column(db.Integer, db.ForeignKey("amenities.id"), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default=BookingStatus.CONFIRMED)
    num_guests = db.Column(db.Integer, default=1)
    notes = db.Column(db.Text, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancel_reason = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id,
                "user_name": self.user.name if self.user else None,
                "amenity_id": self.amenity_id,
                "amenity_name": self.amenity.name if self.amenity else None,
                "amenity_type": self.amenity.amenity_type if self.amenity else None,
                "booking_date": self.booking_date.isoformat(),
                "start_time": self.start_time, "end_time": self.end_time,
                "status": self.status, "num_guests": self.num_guests,
                "notes": self.notes, "created_at": self.created_at.isoformat()}


# ── MAINTENANCE REQUEST ────────────────────────
class MaintenanceRequest(db.Model):
    __tablename__ = "maintenance_requests"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    villa_id = db.Column(db.Integer, db.ForeignKey("villas.id"), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default="normal")
    status = db.Column(db.String(30), default=MaintenanceStatus.OPEN)
    preferred_date = db.Column(db.Date, nullable=True)
    preferred_time_slot = db.Column(db.String(20), nullable=True)
    assigned_to = db.Column(db.String(100), nullable=True)
    assigned_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id,
                "user_name": self.user.name if self.user else None,
                "villa_id": self.villa_id,
                "villa_number": self.villa.villa_number if self.villa else None,
                "category": self.category, "title": self.title,
                "description": self.description, "priority": self.priority,
                "status": self.status,
                "preferred_date": self.preferred_date.isoformat() if self.preferred_date else None,
                "preferred_time_slot": self.preferred_time_slot,
                "assigned_to": self.assigned_to,
                "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
                "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
                "resolution_notes": self.resolution_notes, "rating": self.rating,
                "created_at": self.created_at.isoformat()}


# ── GATE PASS ──────────────────────────────────
class GatePass(db.Model):
    __tablename__ = "gate_passes"
    id = db.Column(db.Integer, primary_key=True)
    pass_code = db.Column(db.String(10), unique=True, nullable=False)
    villa_id = db.Column(db.Integer, db.ForeignKey("villas.id"), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pass_type = db.Column(db.String(20), nullable=False)
    visitor_name = db.Column(db.String(100), nullable=False)
    visitor_phone = db.Column(db.String(20), nullable=True)
    visitor_vehicle = db.Column(db.String(50), nullable=True)
    purpose = db.Column(db.String(200), nullable=True)
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_until = db.Column(db.DateTime, nullable=False)
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_days = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default=GatePassStatus.ACTIVE)
    checked_in_at = db.Column(db.DateTime, nullable=True)
    checked_out_at = db.Column(db.DateTime, nullable=True)
    security_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "pass_code": self.pass_code,
                "villa_id": self.villa_id,
                "villa_number": self.villa.villa_number if self.villa else None,
                "requested_by": self.requested_by,
                "requester_name": self.requested_by_user.name if self.requested_by_user else None,
                "pass_type": self.pass_type, "visitor_name": self.visitor_name,
                "visitor_phone": self.visitor_phone, "visitor_vehicle": self.visitor_vehicle,
                "purpose": self.purpose,
                "valid_from": self.valid_from.isoformat(),
                "valid_until": self.valid_until.isoformat(),
                "is_recurring": self.is_recurring, "recurring_days": self.recurring_days,
                "status": self.status,
                "checked_in_at": self.checked_in_at.isoformat() if self.checked_in_at else None,
                "checked_out_at": self.checked_out_at.isoformat() if self.checked_out_at else None,
                "created_at": self.created_at.isoformat()}


# ── NOTIFICATION ───────────────────────────────
class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notif_type = db.Column(db.String(30), default="info")
    is_read = db.Column(db.Boolean, default=False)
    related_entity = db.Column(db.String(30), nullable=True)
    related_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "message": self.message,
                "notif_type": self.notif_type, "is_read": self.is_read,
                "related_entity": self.related_entity, "related_id": self.related_id,
                "created_at": self.created_at.isoformat()}


# ── PARKING SLOT ───────────────────────────────
class ParkingSlot(db.Model):
    __tablename__ = "parking_slots"
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.String(10), unique=True, nullable=False)
    block = db.Column(db.String(10), nullable=True)
    slot_type = db.Column(db.String(20), default="car")
    status = db.Column(db.String(20), default=ParkingStatus.AVAILABLE)
    assigned_villa_id = db.Column(db.Integer, db.ForeignKey("villas.id"), nullable=True)
    vehicle_number = db.Column(db.String(20), nullable=True)
    vehicle_type = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_villa = db.relationship("Villa", backref="parking_slots", lazy=True)

    def to_dict(self):
        return {"id": self.id, "slot_number": self.slot_number, "block": self.block,
                "slot_type": self.slot_type, "status": self.status,
                "assigned_villa_id": self.assigned_villa_id,
                "villa_number": self.assigned_villa.villa_number if self.assigned_villa else None,
                "vehicle_number": self.vehicle_number, "vehicle_type": self.vehicle_type,
                "notes": self.notes}


# ── BILL ───────────────────────────────────────
class Bill(db.Model):
    __tablename__ = "bills"
    id = db.Column(db.Integer, primary_key=True)
    villa_id = db.Column(db.Integer, db.ForeignKey("villas.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default=BillStatus.UNPAID)
    description = db.Column(db.Text, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    transaction_ref = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    villa = db.relationship("Villa", backref="bills", lazy=True)
    user = db.relationship("User", backref="bills", lazy=True)

    def to_dict(self):
        return {"id": self.id, "villa_id": self.villa_id,
                "villa_number": self.villa.villa_number if self.villa else None,
                "user_id": self.user_id,
                "user_name": self.user.name if self.user else None,
                "title": self.title, "category": self.category, "amount": self.amount,
                "due_date": self.due_date.isoformat(), "status": self.status,
                "description": self.description,
                "paid_at": self.paid_at.isoformat() if self.paid_at else None,
                "payment_method": self.payment_method, "transaction_ref": self.transaction_ref,
                "created_at": self.created_at.isoformat()}


# ── ANNOUNCEMENT ───────────────────────────────
class Announcement(db.Model):
    __tablename__ = "announcements"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default=AnnouncementPriority.NORMAL)
    category = db.Column(db.String(50), default="general")
    posted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    pinned = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship("User", backref="announcements", lazy=True)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "body": self.body,
                "priority": self.priority, "category": self.category,
                "posted_by": self.posted_by,
                "author_name": self.author.name if self.author else None,
                "is_active": self.is_active, "pinned": self.pinned,
                "expires_at": self.expires_at.isoformat() if self.expires_at else None,
                "created_at": self.created_at.isoformat()}

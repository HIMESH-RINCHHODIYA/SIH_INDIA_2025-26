# hostel_models.py
from datetime import datetime
from extensions import db
from models import User

# ==========================================================
# 1. HOSTEL
# ==========================================================
class Hostel(db.Model):
    __tablename__ = "hostels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # Boys / Girls / Mixed / Staff
    address = db.Column(db.String(255))
    warden_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # links to User

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rooms = db.relationship("HostelRoom", back_populates="hostel", lazy="joined")

    def __repr__(self):
        return f"<Hostel id={self.id} name={self.name} type={self.type}>"


# ==========================================================
# 2. HOSTEL ROOMS
# ==========================================================
class HostelRoom(db.Model):
    __tablename__ = "hostel_rooms"

    id = db.Column(db.Integer, primary_key=True)
    hostel_id = db.Column(db.Integer, db.ForeignKey("hostels.id"), nullable=False)

    room_no = db.Column(db.String(50), nullable=False)
    block = db.Column(db.String(50))
    floor = db.Column(db.String(50))

    capacity = db.Column(db.Integer, nullable=False, default=1)
    facilities = db.Column(db.String(255))  # e.g., AC, Wi-Fi, attached bath
    status = db.Column(db.String(50), default="Vacant")  # Vacant / Occupied / Maintenance

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    hostel = db.relationship("Hostel", back_populates="rooms")
    allocations = db.relationship("HostelAllocation", back_populates="room")

    def __repr__(self):
        return f"<Room {self.room_no} cap={self.capacity} status={self.status}>"


# ==========================================================
# 3. HOSTEL ALLOCATION (STUDENT TO ROOM)
# ==========================================================
class HostelAllocation(db.Model):
    __tablename__ = "hostel_allocations"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("hostel_rooms.id"), nullable=False)
    hostel_id = db.Column(db.Integer, db.ForeignKey("hostels.id"), nullable=False)

    admission_date = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(50), default="Active")  # Active / Left / Waiting
    exit_date = db.Column(db.Date)

    # Relationships
    room = db.relationship("HostelRoom", back_populates="allocations")
    student = db.relationship("User", backref=db.backref("hostel_allocation", uselist=False))
    hostel = db.relationship("Hostel", backref="allocations")

    def __repr__(self):
        return f"<Allocation student={self.student_id} room={self.room_id} status={self.status}>"


# ==========================================================
# 4. LEAVE / OUT-PASS
# ==========================================================
class HostelLeave(db.Model):
    __tablename__ = "hostel_leave"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(50), default="Pending")  # Pending / Approved / Rejected
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ Relationships
    student = db.relationship("User", foreign_keys=[student_id], backref="leave_requests")
    approver = db.relationship("User", foreign_keys=[approved_by], backref="approved_leaves")

    def __repr__(self):
        return f"<HostelLeave student={self.student_id} status={self.status}>"


# ==========================================================
# 5. COMPLAINTS / MAINTENANCE
# ==========================================================
class HostelComplaint(db.Model):
    __tablename__ = "hostel_complaints"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    type = db.Column(db.String(100))  # Electrical, Water, Cleanliness
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Open")  # Open / In Progress / Resolved
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    # ✅ Relationships
    student = db.relationship("User", foreign_keys=[student_id], backref="complaints")
    resolver = db.relationship("User", foreign_keys=[resolved_by], backref="resolved_complaints")

    def __repr__(self):
        return f"<Complaint id={self.id} student={self.student_id} status={self.status}>"
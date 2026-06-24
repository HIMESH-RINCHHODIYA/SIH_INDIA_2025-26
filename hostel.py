from datetime import datetime

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from extensions import db
# Hostel-specific models
from hostel_models import (Hostel, HostelAllocation, HostelComplaint,
                           HostelLeave, HostelRoom)
# ✅ MAIN User model from ERP
from models import User

hostel_bp = Blueprint("hostel", __name__, url_prefix="/hostel")


# ===============================
# ADMIN ROUTES
# ===============================


@hostel_bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin_hostel():
    if current_user.role != "Admin":
        return "Unauthorized", 403

    if request.method == "POST":
        # Add Hostel form submission
        name = request.form.get("name")
        code = request.form.get("code")
        hostel_type = request.form.get("type")
        address = request.form.get("address")
        warden_id = request.form.get("warden_id")

        new_hostel = Hostel(
            name=name, code=code, type=hostel_type, address=address, warden_id=warden_id
        )
        db.session.add(new_hostel)
        db.session.commit()
        flash("✅ Hostel created successfully!", "success")
        return redirect(url_for("hostel.admin_hostel"))

    hostels = Hostel.query.all()
    return render_template("templates-hostel/admin_hostel.html", hostels=hostels)


@hostel_bp.route("/admin/add_room", methods=["POST"])
@login_required
def add_room():
    if current_user.role != "Admin":
        return "Unauthorized", 403

    hostel_id = request.form.get("hostel_id")
    room_no = request.form.get("room_no")
    block = request.form.get("block")
    floor = request.form.get("floor")
    capacity = request.form.get("capacity")
    facilities = request.form.get("facilities")

    new_room = HostelRoom(
        hostel_id=hostel_id,
        room_no=room_no,
        block=block,
        floor=floor,
        capacity=capacity,
        facilities=facilities,
    )
    db.session.add(new_room)
    db.session.commit()
    flash("✅ Room added successfully!", "success")

    return redirect(url_for("hostel.admin_hostel"))


@hostel_bp.route("/admin/allocation", methods=["GET", "POST"])
@login_required
def admin_allocation():
    if current_user.role != "Admin":
        return "Unauthorized", 403

    if request.method == "POST":
        student_id = int(request.form.get("student_id"))
        room_id = int(request.form.get("room_id"))

        room = HostelRoom.query.get(room_id)

        # ✅ Capacity check - don’t over-allocate
        if len(room.allocations) >= room.capacity:
            flash(
                f"⚠️ Room {room.room_no} in {room.hostel.name} is already full!",
                "danger",
            )
            return redirect(url_for("hostel.admin_allocation"))

        # ✅ Prevent allocating same student twice
        existing = HostelAllocation.query.filter_by(
            student_id=student_id, status="Active"
        ).first()
        if existing:
            flash("⚠️ Student already has an active hostel allocation!", "warning")
            return redirect(url_for("hostel.admin_allocation"))

        allocation = HostelAllocation(student_id=student_id, room_id=room_id)
        db.session.add(allocation)
        db.session.commit()
        flash("✅ Room allocated to student!", "success")
        return redirect(url_for("hostel.admin_allocation"))

    allocations = HostelAllocation.query.all()
    rooms = HostelRoom.query.all()
    students = User.query.filter_by(role="Student").all()
    return render_template(
        "templates-hostel/admin_allocation.html",
        allocations=allocations,
        rooms=rooms,
        students=students,
    )


@hostel_bp.route("/admin/reports")
@login_required
def admin_reports():
    if current_user.role != "Admin":
        return "Unauthorized", 403

    hostels = Hostel.query.all()

    total_rooms = HostelRoom.query.count()
    total_allocations = HostelAllocation.query.filter_by(status="Active").count()
    total_capacity = sum(r.capacity for r in HostelRoom.query.all())
    vacant_beds = total_capacity - total_allocations

    # Leave stats
    total_leaves = HostelLeave.query.count()
    pending_leaves = HostelLeave.query.filter_by(status="Pending").count()
    approved_leaves = HostelLeave.query.filter_by(status="Approved").count()

    # Complaint stats
    total_complaints = HostelComplaint.query.count()
    open_complaints = HostelComplaint.query.filter_by(status="Open").count()
    inprogress_complaints = HostelComplaint.query.filter_by(
        status="In Progress"
    ).count()
    resolved_complaints = HostelComplaint.query.filter_by(status="Resolved").count()

    return render_template(
        "templates-hostel/admin_reports.html",
        hostels=hostels,
        total_rooms=total_rooms,
        total_capacity=total_capacity,
        total_allocations=total_allocations,
        vacant_beds=vacant_beds,
        total_leaves=total_leaves,
        pending_leaves=pending_leaves,
        approved_leaves=approved_leaves,
        total_complaints=total_complaints,
        open_complaints=open_complaints,
        inprogress_complaints=inprogress_complaints,
        resolved_complaints=resolved_complaints,
    )


@hostel_bp.route("/admin/complaints")
@login_required
def admin_complaints():
    if current_user.role != "Admin":
        return "Unauthorized", 403

    filter_status = request.args.get("filter")
    if filter_status:
        complaints = (
            HostelComplaint.query.filter_by(status=filter_status)
            .order_by(HostelComplaint.created_at.desc())
            .all()
        )
    else:
        complaints = HostelComplaint.query.order_by(
            HostelComplaint.created_at.desc()
        ).all()

    return render_template(
        "templates-hostel/admin_complaints.html",
        complaints=complaints,
        filter=filter_status,
    )


@hostel_bp.route("/admin/complaints/update/<int:complaint_id>", methods=["POST"])
@login_required
def update_complaint(complaint_id):
    if current_user.role != "Admin":
        return "Unauthorized", 403

    status = request.form.get("status")
    complaint = HostelComplaint.query.get_or_404(complaint_id)

    complaint.status = status
    if status == "Resolved":
        complaint.resolved_by = current_user.id
        complaint.resolved_at = datetime.utcnow()

    db.session.commit()
    flash(f"Complaint #{complaint.id} status updated to {status}", "success")
    return redirect(url_for("hostel.admin_complaints"))


# ===============================
# ADMIN Leave Management
# ===============================


@hostel_bp.route("/admin/leaves")
@login_required
def admin_leaves():
    if current_user.role != "Admin":
        return "Unauthorized", 403

    filter_status = request.args.get("filter")
    if filter_status:
        leaves = (
            HostelLeave.query.filter_by(status=filter_status)
            .order_by(HostelLeave.created_at.desc())
            .all()
        )
    else:
        leaves = HostelLeave.query.order_by(HostelLeave.created_at.desc()).all()

    return render_template(
        "templates-hostel/admin_leaves.html", leaves=leaves, filter=filter_status
    )


@hostel_bp.route("/admin/leaves/update/<int:leave_id>", methods=["POST"])
@login_required
def update_leave(leave_id):
    if current_user.role != "Admin":
        return "Unauthorized", 403

    status = request.form.get("status")
    leave = HostelLeave.query.get_or_404(leave_id)

    leave.status = status
    if status in ["Approved", "Rejected"]:
        leave.approved_by = current_user.id

    db.session.commit()
    flash(f"Leave #{leave.id} updated to {status}", "success")
    return redirect(url_for("hostel.admin_leaves"))


# ===============================
# STUDENT ROUTES
# ===============================
@hostel_bp.route("/student")
@login_required
def student_hostel():
    if current_user.role != "Student":
        return "Unauthorized", 403

    # Active hostel allocation
    allocation = HostelAllocation.query.filter_by(
        student_id=current_user.id, status="Active"
    ).first()

    # Leave requests
    leaves = (
        HostelLeave.query.filter_by(student_id=current_user.id)
        .order_by(HostelLeave.created_at.desc())
        .all()
    )

    # Complaints
    complaints = (
        HostelComplaint.query.filter_by(student_id=current_user.id)
        .order_by(HostelComplaint.created_at.desc())
        .all()
    )

    # Placeholder finance (integrate with ERP later)
    fee_status = "Paid"
    fee_amount = "20000"
    due_date = "2024-07-01"

    return render_template(
        "templates-hostel/student_hostel.html",
        allocation=allocation,
        leaves=leaves,
        complaints=complaints,  # ✅ pass complaints
        fee_status=fee_status,
        fee_amount=fee_amount,
        due_date=due_date,
    )


@hostel_bp.route("/student/leave", methods=["POST"])
@login_required
def submit_leave():
    if current_user.role != "Student":
        return "Unauthorized", 403

    from_date_str = request.form.get("from_date")
    to_date_str = request.form.get("to_date")
    reason = request.form.get("reason")

    from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
    to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()

    leave_request = HostelLeave(
        student_id=current_user.id, from_date=from_date, to_date=to_date, reason=reason
    )
    db.session.add(leave_request)
    db.session.commit()
    flash("📩 Leave request submitted successfully!", "success")

    return redirect(url_for("hostel.student_hostel"))


@hostel_bp.route("/student/complaint", methods=["POST"])
@login_required
def submit_complaint():
    if current_user.role != "Student":
        return "Unauthorized", 403

    complaint_type = request.form.get("type")
    description = request.form.get("description")

    complaint = HostelComplaint(
        student_id=current_user.id, type=complaint_type, description=description
    )
    db.session.add(complaint)
    db.session.commit()
    flash("📝 Complaint submitted successfully!", "success")

    return redirect(url_for("hostel.student_hostel"))


@hostel_bp.route("/api/list")
@login_required
def api_hostel_list():
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    hostels = Hostel.query.all()
    return jsonify(
        [
            {
                "id": h.id,
                "name": h.name,
                "type": h.type,
                "capacity": sum(room.capacity for room in h.rooms),
                "occupied": sum(len(room.allocations) for room in h.rooms),
            }
            for h in hostels
        ]
    )

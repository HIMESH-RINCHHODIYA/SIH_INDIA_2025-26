from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models import Attendance
from datetime import datetime

# Create Blueprint
student_bp = Blueprint("student_bp", __name__, template_folder="templates")

@student_bp.route('/student/attendance', methods=['GET'])
@login_required
def student_attendance():
    if current_user.role != "Student":
        return "Unauthorized", 403

    # Base query for current student
    query = Attendance.query.filter_by(student_id=current_user.id)

    # Filters from GET params
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    start_date_obj = None
    end_date_obj = None

    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date >= start_date_obj)
        except ValueError:
            start_date_obj = None
            start_date = ""

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date <= end_date_obj)
        except ValueError:
            end_date_obj = None
            end_date = ""

    # Fetch attendance records
    attendance_records = query.order_by(Attendance.date.desc()).all()

    # Summary stats
    total_classes = len(attendance_records)
    present_count = sum(1 for a in attendance_records if a.status == "Present")
    absent_count = sum(1 for a in attendance_records if a.status == "Absent")
    percentage = round((present_count / total_classes) * 100, 2) if total_classes > 0 else 0

    return render_template(
        "student_attendance.html",
        attendance_records=attendance_records,
        total_classes=total_classes,
        present_count=present_count,
        absent_count=absent_count,
        percentage=percentage,
        start_date=start_date if start_date else "",
        end_date=end_date if end_date else ""
    )

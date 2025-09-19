from flask import Blueprint, render_template, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from models import Attendance, Course

faculty_stud_bp = Blueprint("faculty_stud_bp", __name__, template_folder="templates")

def summarize_attendance(records):
    total = len(records)
    present = sum(1 for r in records if r.status.lower() == "present")
    absent = total - present
    percentage = round((present / total) * 100, 2) if total > 0 else 0
    return total, present, absent, percentage

# 📌 Faculty Attendance (view students in their course)
@faculty_stud_bp.route("/attendance", methods=["GET"])
@login_required
def faculty_attendance():
    if current_user.role.lower() != "faculty":
        return "Unauthorized", 403

    # Optional: faculty selects a course
    course_id = request.args.get("course_id", type=int)
    if not course_id:
        flash("Please select a course to view attendance.", "warning")
        return render_template("faculty_attendance.html", attendance_records=[])

    # Query attendance for that course
    query = Attendance.query.filter_by(course_id=course_id)

    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    start_date_obj, end_date_obj = None, None

    try:
        if start_date:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid start date format. Use YYYY-MM-DD.", "warning")
        start_date = ""

    try:
        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid end date format. Use YYYY-MM-DD.", "warning")
        end_date = ""

    if start_date_obj:
        query = query.filter(Attendance.date >= start_date_obj)
    if end_date_obj:
        query = query.filter(Attendance.date <= end_date_obj)

    records = query.order_by(Attendance.date.desc()).all()
    total, present, absent, percentage = summarize_attendance(records)

    course = Course.query.get(course_id)

    return render_template(
        "faculty_attendance.html",
        attendance_records=records,
        total_classes=total,
        present_count=present,
        absent_count=absent,
        percentage=percentage,
        faculty_name=current_user.name,
        course_name=course.course_name if course else "Unknown",
        start_date=start_date,
        end_date=end_date,
    )

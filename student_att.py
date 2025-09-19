# student_att.py

from flask import Blueprint, render_template, request, flash
from flask_login import login_required, current_user
from datetime import datetime
# ✅ ADDED Course and StudentCourse models to the import
from models import Attendance, Course, StudentCourse

student_bp = Blueprint("student_bp", __name__, template_folder="templates")

def summarize_attendance(records):
    total = len(records)
    present = sum(1 for r in records if r.status.lower() == "present")
    absent = total - present
    percentage = round((present / total) * 100, 2) if total > 0 else 0
    return total, present, absent, percentage

# 📌 Student Attendance
@student_bp.route("/attendance", methods=["GET"])
@login_required
def student_attendance():
    if current_user.role.lower() != "student":
        return "Unauthorized", 403

    # ✅ STEP 1: Fetch ONLY the courses the student is enrolled in.
    enrolled_courses = Course.query.join(StudentCourse).filter(
        StudentCourse.student_id == current_user.id
    ).order_by(Course.course_name).all()

    # Filters
    # ✅ ADDED course_id filter
    selected_course_id = request.args.get("course_id", "")
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

    # Query only this student's attendance
    query = Attendance.query.filter_by(student_id=current_user.id)
    
    # ✅ ADDED filter for selected course
    if selected_course_id:
        query = query.filter(Attendance.course_id == selected_course_id)
    if start_date_obj:
        query = query.filter(Attendance.date >= start_date_obj)
    if end_date_obj:
        query = query.filter(Attendance.date <= end_date_obj)

    records = query.order_by(Attendance.date.desc()).all()
    total, present, absent, percentage = summarize_attendance(records)

    # ✅ STEP 2: Calculate the course-wise summary for the table
    course_summary = []
    # Use all enrolled courses for the summary table, but calculations are based on filtered records
    all_student_records = Attendance.query.filter_by(student_id=current_user.id).all()

    for course in enrolled_courses:
        # Filter records for the current course from the full list
        records_for_course = [r for r in all_student_records if r.course_id == course.id]
        total_c, present_c, _, percentage_c = summarize_attendance(records_for_course)
        
        if total_c > 0: # Only add courses with attendance records to the summary
            course_summary.append({
                'course': course,
                'total': total_c,
                'present': present_c,
                'absent': total_c - present_c,
                'percentage': percentage_c
            })


    return render_template(
        "student_attendance.html",
        # Original data
        attendance_records=records,
        total_classes=total,
        present_count=present,
        absent_count=absent,
        percentage=percentage,
        student_name=current_user.name,
        student_roll=current_user.roll_no,
        student_program=current_user.program or "",
        student_branch=current_user.branch or "",
        student_year=current_user.year or "",
        student_section=current_user.section or "", # Note: HTML uses student_sem
        # ✅ STEP 3: Pass new data to the template
        courses=enrolled_courses,
        course_summary=course_summary,
        # Pass filter values back to keep them selected
        start_date=start_date,
        end_date=end_date,
        selected_course_id=selected_course_id
    )
from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from faculty_attendance import faculty_stud_bp
from models import Attendance, Course, StudentCourse, User


def _student_query(program, branch, year, semester, section, course_id=None):
    query = User.query.filter_by(
        role="Student",
        program=program,
        branch=branch,
        year=year,
        semester=semester,
        section=section,
    )
    if course_id:
        query = query.join(
            StudentCourse, StudentCourse.student_id == User.id
        ).filter(StudentCourse.course_id == course_id).distinct()
    return query.order_by(User.roll_no)


def _selected_filters(source):
    return {
        "program": source.get("program", ""),
        "branch": source.get("branch", ""),
        "year": source.get("year", ""),
        "semester": source.get("semester", ""),
        "section": source.get("section", ""),
        "course_id": source.get("course_id", type=int),
        "date": source.get("date") or datetime.today().strftime("%Y-%m-%d"),
    }


def _authorized():
    return current_user.role in {"Faculty", "Admin", "SuperAdmin"}


def _available_courses(filters):
    cohort = ("program", "branch", "year", "semester")
    if not all(filters[key] for key in cohort):
        return []

    if current_user.role == "Faculty":
        assignments = current_user.faculty_courses.filter_by(
            program=filters["program"],
            branch=filters["branch"],
            year=filters["year"],
            semester=filters["semester"],
        ).all()
        course_ids = {assignment.course_id for assignment in assignments}
        if not course_ids:
            return []
        return Course.query.filter(Course.id.in_(course_ids)).order_by(Course.course_name).all()

    return Course.query.order_by(Course.course_name).all()


@faculty_stud_bp.route("/attendance/courses")
@login_required
def attendance_courses():
    if not _authorized():
        return jsonify({"error": "Unauthorized"}), 403

    filters = _selected_filters(request.args)
    courses = _available_courses(filters)
    return jsonify([{"id": course.id, "name": course.course_name} for course in courses])


@faculty_stud_bp.route("/attendance", methods=["GET", "POST"])
@login_required
def faculty_attendance():
    if not _authorized():
        flash("Unauthorized access.", "danger")
        return redirect(url_for("dashboard"))

    filters = _selected_filters(request.form if request.method == "POST" else request.args)
    courses = _available_courses(filters)
    students = []
    cohort = ("program", "branch", "year", "semester", "section")
    if all(filters[key] for key in cohort) and filters["course_id"]:
        if not any(course.id == filters["course_id"] for course in courses):
            flash("Select a course assigned to this cohort.", "warning")
            filters["course_id"] = None
        else:
            students = _student_query(
                filters["program"], filters["branch"], filters["year"],
                filters["semester"], filters["section"], filters["course_id"],
            ).all()

    if students:
        try:
            selected_date = datetime.strptime(filters["date"], "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "warning")
            filters["date"] = datetime.today().strftime("%Y-%m-%d")
            selected_date = datetime.strptime(filters["date"], "%Y-%m-%d").date()

        records = Attendance.query.filter(
            Attendance.student_id.in_([student.id for student in students]),
            Attendance.date == selected_date,
            Attendance.course_id == filters["course_id"],
        ).all()
        attendance_map = {record.student_id: record.status for record in records}
        remarks_map = {record.student_id: record.remarks for record in records}
    else:
        attendance_map = {}
        remarks_map = {}

    return render_template(
        "faculty_stud.html",
        students=students,
        courses=courses,
        attendance_map=attendance_map,
        remarks_map=remarks_map,
        selected_program=filters["program"],
        selected_branch=filters["branch"],
        selected_year=filters["year"],
        selected_semester=filters["semester"],
        selected_section=filters["section"],
        selected_course_id=filters["course_id"],
        selected_date=filters["date"],
    )


@faculty_stud_bp.route("/attendance/save", methods=["POST"])
@login_required
def save_attendance():
    if not _authorized():
        flash("Unauthorized access.", "danger")
        return redirect(url_for("dashboard"))

    filters = _selected_filters(request.form)
    try:
        selected_date = datetime.strptime(filters["date"], "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("faculty_stud_bp.faculty_attendance"))

    cohort = ["program", "branch", "year", "semester", "section"]
    if not all(filters[key] for key in cohort) or not filters["course_id"]:
        flash("Select the complete cohort and a course before saving attendance.", "warning")
        return redirect(url_for("faculty_stud_bp.faculty_attendance"))

    courses = _available_courses(filters)
    if not any(course.id == filters["course_id"] for course in courses):
        flash("Select a course assigned to this cohort.", "warning")
        return redirect(url_for("faculty_stud_bp.faculty_attendance"))

    students = _student_query(
        filters["program"], filters["branch"], filters["year"],
        filters["semester"], filters["section"], filters["course_id"],
    ).all()

    for student in students:
        present = request.form.get(f"attendance_{student.id}") == "on"
        record = Attendance.query.filter_by(
            student_id=student.id,
            date=selected_date,
            course_id=filters["course_id"],
        ).first()
        if record is None:
            record = Attendance(
                student_id=student.id,
                course_id=filters["course_id"],
                date=selected_date,
                branch=filters["branch"],
                class_name=filters["year"],
            )
            db.session.add(record)
        record.status = "Present" if present else "Absent"
        record.remarks = None if present else request.form.get(f"remark_{student.id}") or None

    db.session.commit()
    flash("Attendance saved successfully.", "success")
    return redirect(url_for("faculty_stud_bp.faculty_attendance", **filters))

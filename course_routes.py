from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from extensions import db
from models import Course, StudentCourse, FacultyCourse, User

course_bp = Blueprint("course_bp", __name__)

# -------------------- Admin: Add Course --------------------
@course_bp.route("/add_course", methods=["POST"])
@login_required
def add_course():
    if current_user.role != "Admin":
        flash("⛔ Access Denied.", "danger")
        return redirect(url_for("course_bp.admin_courses"))

    course_name = request.form.get("course_name")
    course_code = request.form.get("course_code")

    if not course_name or not course_code:
        flash("❌ Course Name and Code are required.", "danger")
        return redirect(url_for("course_bp.admin_courses"))

    existing = Course.query.filter(
        (Course.course_name == course_name) | (Course.course_code == course_code)
    ).first()
    if existing:
        flash("⚠️ Course already exists.", "warning")
        return redirect(url_for("course_bp.admin_courses"))

    new_course = Course(course_name=course_name, course_code=course_code)
    db.session.add(new_course)
    db.session.commit()

    flash(f"✅ Course '{course_name}' added successfully!", "success")
    return redirect(url_for("course_bp.admin_courses"))


# -------------------- Admin: Manage Courses --------------------
@course_bp.route("/admin/courses")
@login_required
def admin_courses():
    if current_user.role != "Admin":
        flash("⛔ Access Denied.", "danger")
        return redirect(url_for("dashboard"))

    courses = Course.query.all()
    return render_template("admin_course.html", courses=courses)


# -------------------- Student: View & Enroll in Courses --------------------
@course_bp.route("/student/courses", methods=["GET", "POST"])
@login_required
def student_courses():
    if current_user.role != "Student":
        flash("⛔ Access Denied.", "danger")
        return redirect(url_for("dashboard"))

    courses = Course.query.all()

    if request.method == "POST":
        course_id = request.form.get("course_id")
        if not course_id:
            flash("❌ Please select a course.", "danger")
            return redirect(url_for("course_bp.student_courses"))

        # Check if already enrolled
        existing = StudentCourse.query.filter_by(student_id=current_user.id, course_id=course_id).first()
        if existing:
            flash("⚠️ You are already enrolled in this course.", "warning")
            return redirect(url_for("course_bp.student_courses"))

        # Auto-fill program, branch, year from User profile
        enrollment = StudentCourse(
            student_id=current_user.id,
            course_id=course_id,
            program=current_user.program,
            branch=current_user.branch,
            year=current_user.year
        )
        db.session.add(enrollment)
        db.session.commit()

        flash("✅ Successfully enrolled in course!", "success")
        return redirect(url_for("course_bp.student_courses"))

    enrolled_courses = StudentCourse.query.filter_by(student_id=current_user.id).all()
    return render_template("student_courses.html", courses=courses, enrolled=enrolled_courses)


# -------------------- Faculty: Assign Teaching Courses --------------------
@course_bp.route("/faculty/courses", methods=["GET", "POST"])
@login_required
def faculty_courses():
    if current_user.role != "Faculty":
        flash("⛔ Access Denied.", "danger")
        return redirect(url_for("dashboard"))

    courses = Course.query.all()

    if request.method == "POST":
        course_id = request.form.get("course_id")
        program = request.form.get("program")
        branch = request.form.get("branch")
        year = request.form.get("year")
        is_theory = request.form.get("is_theory") == "true"

        if not all([course_id, program, branch, year]):
            flash("❌ All fields are required.", "danger")
            return redirect(url_for("course_bp.faculty_courses"))

        # Check if already assigned
        existing = FacultyCourse.query.filter_by(
            faculty_id=current_user.id, course_id=course_id, program=program, branch=branch, year=year
        ).first()
        if existing:
            flash("⚠️ You are already assigned to this course.", "warning")
            return redirect(url_for("course_bp.faculty_courses"))

        assignment = FacultyCourse(
            faculty_id=current_user.id,
            course_id=course_id,
            program=program,
            branch=branch,
            year=year,
            is_theory=is_theory
        )
        db.session.add(assignment)
        db.session.commit()

        flash("✅ Course assigned successfully!", "success")
        return redirect(url_for("course_bp.faculty_courses"))

    assigned_courses = FacultyCourse.query.filter_by(faculty_id=current_user.id).all()
    return render_template("faculty_courses.html", courses=courses, assigned=assigned_courses)

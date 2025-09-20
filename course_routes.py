from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from extensions import db
from models import Course, StudentCourse, FacultyCourse, User  # ✅ use singular consistently

course_bp = Blueprint("course_bp", __name__)

# -------------------- Admin: Add Course -------------------- #
# -------------------- Admin: Add Course -------------------- #
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

    # Prevent duplicates
    existing = Course.query.filter(
        (Course.course_name == course_name) | (Course.course_code == course_code)
    ).first()
    if existing:
        flash("⚠️ Course already exists.", "warning")
        return redirect(url_for("course_bp.admin_courses"))

    # ✅ Only store the fields actually defined in Course model
    new_course = Course(
        course_name=course_name,
        course_code=course_code
    )
    db.session.add(new_course)
    db.session.commit()

    flash(f"✅ Course '{course_name}' added successfully!", "success")
    return redirect(url_for("course_bp.admin_courses"))


# -------------------- Admin: Manage Courses -------------------- #
@course_bp.route("/admin/course")
@login_required
def admin_courses():
    if current_user.role != "Admin":
        flash("⛔ Access Denied.", "danger")
        return redirect(url_for("dashboard"))

    courses = Course.query.all()
    return render_template("admin_course.html", courses=courses)


# FILE: courses_routes.py

# -------------------- Student: View & Enroll in Courses -------------------- #
@course_bp.route("/student/courses", methods=["GET", "POST"])
@login_required
def student_courses():
    # 1. Role Check
    if current_user.role != "Student":
        flash("⛔ Access Denied.", "danger")
        return redirect(url_for("dashboard"))

    # 2. Handle Enrollment POST Request
    if request.method == "POST":
        course_id = request.form.get("course_id")
        if not course_id:
            flash("❌ Please select a course.", "danger")
            return redirect(url_for("course_bp.student_courses"))

        # Check if already enrolled
        existing = StudentCourse.query.filter_by(
            student_id=current_user.id, course_id=course_id
        ).first()
        if existing:
            flash("⚠️ You are already enrolled in this course.", "warning")
            return redirect(url_for("course_bp.student_courses"))

        # Create new enrollment
        enrollment = StudentCourse(
            student_id=current_user.id,
            course_id=course_id,
            program=current_user.program,
            branch=current_user.branch,
            year=current_user.year,
            semester=current_user.semester,
        )
        db.session.add(enrollment)
        db.session.commit()

        flash("✅ Successfully enrolled in course!", "success")
        return redirect(url_for("course_bp.student_courses"))

    # 3. Prepare Data for GET Request
    
    # Set a reliable default photo path
    photo_path = "uploads/default.png"
    # If the user has a photo, process its path to remove the 'static/' prefix
    if current_user.photo:
        photo_path = current_user.photo.replace("static/", "")

    # Fetch all data needed for the template
    all_courses = Course.query.all()
    enrolled_courses = StudentCourse.query.filter_by(student_id=current_user.id).all()

    # 4. Render the template with clean data
    return render_template(
        "student_courses.html",
        courses=all_courses,
        enrolled=enrolled_courses,
        student_photo_path=photo_path  # Pass the corrected path to the template
    )
# -------------------- Faculty: Assign Teaching Courses -------------------- #
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
        semester = request.form.get("semester")
        course_type = request.form.get("course_type")

        if not all([course_id, program, branch, year, semester, course_type]):
            flash("❌ All fields are required.", "danger")
            return redirect(url_for("course_bp.faculty_courses"))

        # Check if already assigned
        existing = FacultyCourse.query.filter_by(
            faculty_id=current_user.id,
            course_id=course_id,
            program=program,
            branch=branch,
            year=year,
            semester=semester,
            course_type=course_type
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
            semester=semester,
            course_type=course_type
        )
        db.session.add(assignment)
        db.session.commit()

        flash("✅ Course assigned successfully!", "success")
        return redirect(url_for("course_bp.faculty_courses"))

    assigned_courses = FacultyCourse.query.filter_by(faculty_id=current_user.id).all()
    return render_template("faculty_courses.html", courses=courses, assigned=assigned_courses)

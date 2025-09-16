from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, Result
from extensions import db
import datetime

grades_bp = Blueprint("grades_bp", __name__, template_folder="templates")

# ===========================
# Student View - See Own Results
# ===========================
@grades_bp.route("/student/grades", methods=["GET"])
@login_required
def student_grades():
    if current_user.role != "Student":
        flash("Unauthorized access", "danger")
        return redirect(url_for("student_pages"))  # Redirect to student dashboard

    semester = request.args.get("semester")
    query = Result.query.filter_by(student_id=current_user.id, approved_by_admin=True)
    if semester:
        query = query.filter_by(semester=semester)

    results = query.order_by(Result.semester.desc()).all()
    semesters = sorted(
        {r.semester for r in Result.query.filter_by(student_id=current_user.id).all()},
        reverse=True
    )

    return render_template(
        "student_grades.html",
        results=results,
        semesters=semesters,
        selected_semester=semester
    )


# ===========================
# Faculty View - Upload Marks
# ===========================
@grades_bp.route("/faculty/grades/upload", methods=["GET", "POST"])
@login_required
def faculty_upload_grades():
    if current_user.role != "Faculty":
        flash("Unauthorized access", "danger")
        return redirect(url_for("grades_bp.student_grades"))

    if request.method == "POST":
        student_id = request.form.get("student_id")
        course_code = request.form.get("course_code")
        course_name = request.form.get("course_name")
        semester = request.form.get("semester")
        marks_input = request.form.get("marks")

        # Validation
        if not all([student_id, course_code, course_name, semester, marks_input]):
            flash("Please fill all required fields", "danger")
            return redirect(url_for("grades_bp.faculty_upload_grades"))

        try:
            marks = int(marks_input)
        except ValueError:
            flash("Marks must be a number", "danger")
            return redirect(url_for("grades_bp.faculty_upload_grades"))

        # Grade calculation
        grade = "F"
        if marks >= 90: grade = "A+"
        elif marks >= 80: grade = "A"
        elif marks >= 70: grade = "B+"
        elif marks >= 60: grade = "B"
        elif marks >= 50: grade = "C"
        elif marks >= 40: grade = "D"

        result = Result(
            student_id=student_id,
            course_code=course_code,
            course_name=course_name,
            semester=semester,
            marks=marks,
            grade=grade,
            approved_by_admin=False,
            created_at=datetime.datetime.utcnow()
        )
        db.session.add(result)
        db.session.commit()

        flash("✅ Result uploaded successfully (pending admin approval)", "success")
        return redirect(url_for("grades_bp.faculty_upload_grades"))

    # Fetch students
    students = User.query.filter_by(role="Student").all()
    return render_template("faculty_grades_upload.html", students=students)


# ===========================
# Admin View - Approve Results
# ===========================
@grades_bp.route("/admin/grades/approve", methods=["GET", "POST"])
@login_required
def admin_approve_grades():
    if current_user.role != "Admin":
        flash("Unauthorized access", "danger")
        return redirect(url_for("grades_bp.student_grades"))

    pending_results = Result.query.filter_by(approved_by_admin=False).order_by(Result.created_at.desc()).all()

    if request.method == "POST":
        approved_ids = request.form.getlist("approve")
        for rid in approved_ids:
            result = db.session.get(Result, int(rid))
            if result:
                result.approved_by_admin = True
        db.session.commit()
        flash("✅ Selected results approved", "success")
        return redirect(url_for("grades_bp.admin_approve_grades"))

    return render_template("admin_grades_approve.html", results=pending_results)

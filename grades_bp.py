from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, Result, Course, db  # Correct imports
from sqlalchemy import distinct

grades_bp = Blueprint("grades_bp", __name__, template_folder="templates")

def calculate_grade(marks):
    """Helper function to calculate grade from marks."""
    try:
        marks = int(marks)
        if marks >= 90: return "A+"
        elif marks >= 80: return "A"
        elif marks >= 70: return "B+"
        elif marks >= 60: return "B"
        elif marks >= 50: return "C"
        elif marks >= 40: return "D"
        else: return "F"
    except (ValueError, TypeError):
        return "N/A"

# ===========================
# Student View - See Own Results
# ===========================
@grades_bp.route("/student/grades")
@login_required
def student_grades():
    if current_user.role != "Student":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.index")) # Adjust to your main/home route

    selected_semester = request.args.get("semester")
    
    query = Result.query.filter_by(
        student_id=current_user.id,
        approved_by_admin=True
    )

    if selected_semester:
        query = query.filter(Result.semester == selected_semester)
    
    results = query.all()
    
    semesters_query = db.session.query(distinct(Result.semester)).filter_by(student_id=current_user.id).all()
    semesters = sorted([s[0] for s in semesters_query], reverse=True)

    return render_template(
        "student_grades.html",
        results=results,
        semesters=semesters,
        selected_semester=selected_semester
    )

# ===========================
# Faculty View - Upload Marks
# ===========================
@grades_bp.route("/faculty/grades/upload", methods=["GET", "POST"])
@login_required
def faculty_upload_grades():
    if current_user.role != "Faculty":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        student_id = request.form.get("student_id")
        course_code = request.form.get("course_code")
        course_name = request.form.get("course_name")
        semester = request.form.get("semester")
        marks_input = request.form.get("marks")

        if not all([student_id, course_code, course_name, semester, marks_input]):
            flash("Please fill all required fields", "danger")
            return redirect(url_for("grades_bp.faculty_upload_grades"))

        # =================================================================
        # CORE FIX: Find or create the Course, then use its ID for the Result
        # =================================================================
        
        # Step 1: Find the course by its unique code.
        course = Course.query.filter_by(course_code=course_code).first()

        # Step 2: If the course doesn't exist, create it.
        if not course:
            course = Course(course_name=course_name, course_code=course_code)
            db.session.add(course)
            db.session.commit() # Commit here to generate the new course.id

        # Step 3: Now, create the Result object using the correct 'course_id'
        result = Result(
            student_id=student_id,
            course_id=course.id, # <-- THIS IS THE FIX
            semester=semester,
            marks=int(marks_input),
            grade=calculate_grade(marks_input),
            approved_by_admin=False
        )
        db.session.add(result)
        db.session.commit()

        flash("✅ Result uploaded successfully (pending admin approval)", "success")
        return redirect(url_for("grades_bp.faculty_upload_grades"))

    students = User.query.filter_by(role="Student").all()
    return render_template("faculty_grades_upload.html", students=students)


# ===========================
# Admin View - Approve Results
# ===========================
@grades_bp.route("/admin/grades/approve", methods=["GET", "POST"])
@login_required
def admin_approve_grades():
    if current_user.role != "Admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        approved_ids = request.form.getlist("approve")
        for rid in approved_ids:
            result = db.session.get(Result, int(rid))
            if result:
                result.approved_by_admin = True
        db.session.commit()
        flash("✅ Selected results approved", "success")
        return redirect(url_for("grades_bp.admin_approve_grades"))

    pending_results = Result.query.filter_by(approved_by_admin=False).order_by(Result.created_at.desc()).all()
    return render_template("admin_grades_approve.html", results=pending_results)


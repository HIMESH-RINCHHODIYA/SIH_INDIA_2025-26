from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from models import User, Result, Course, College, db
from sqlalchemy import distinct
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from datetime import datetime
import io

grades_bp = Blueprint("grades_bp", __name__, template_folder="templates")

# ===========================
# Helper - Calculate Grade
# ===========================
def calculate_grade(marks):
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
        return redirect(url_for("main.index"))

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
# PDF Download for Student Grades
# ===========================
@grades_bp.route("/student/grades/pdf")
@login_required
def student_grades_pdf():
    if current_user.role != "Student":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.index"))

    selected_semester = request.args.get("semester")

    query = Result.query.filter_by(
        student_id=current_user.id,
        approved_by_admin=True
    )
    if selected_semester:
        query = query.filter(Result.semester == selected_semester)

    results = query.all()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, height - 50, current_user.college.name if current_user.college else "My College")

    # Logo (if exists)
    if current_user.college and current_user.college.logo:
        try:
            pdf.drawImage(current_user.college.logo, 50, height - 100, width=80, preserveAspectRatio=True, mask="auto")
        except:
            pass  # ignore errors if logo path is invalid

    # Student Info
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 120, f"Name: {current_user.name}")
    pdf.drawString(50, height - 140, f"Enrollment No: {current_user.enrollment_no or 'N/A'}")
    pdf.drawString(50, height - 160, f"Program: {current_user.program or 'N/A'}")
    pdf.drawString(50, height - 180, f"Semester: {selected_semester or 'All'}")
    pdf.drawString(50, height - 200, f"Date Generated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")

    # Table Header
    pdf.setFont("Helvetica-Bold", 11)
    y = height - 240
    pdf.drawString(50, y, "Course Code")
    pdf.drawString(150, y, "Course Name")
    pdf.drawString(350, y, "Marks")
    pdf.drawString(420, y, "Grade")
    y -= 20

    # Table Content
    pdf.setFont("Helvetica", 11)
    for r in results:
        pdf.drawString(50, y, r.course.course_code if r.course else "-")
        pdf.drawString(150, y, r.course.course_name if r.course else "-")
        pdf.drawString(350, y, str(r.marks))
        pdf.drawString(420, y, r.grade)
        y -= 20
        if y < 100:  # New page if too long
            pdf.showPage()
            y = height - 100

    # Footer with Digital Signature
    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawString(50, 80, "This is a digitally generated result sheet and does not require a physical signature.")
    pdf.drawString(width - 200, 60, "Authorized Signatory")
    pdf.line(width - 220, 70, width - 50, 70)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=grades_{current_user.id}.pdf"
    return response

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

        course = Course.query.filter_by(course_code=course_code).first()
        if not course:
            course = Course(course_name=course_name, course_code=course_code)
            db.session.add(course)
            db.session.commit()

        result = Result(
            student_id=student_id,
            course_id=course.id,
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

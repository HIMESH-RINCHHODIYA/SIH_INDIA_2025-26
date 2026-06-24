import io
import csv
import openpyxl
from datetime import datetime

from flask import (
    Blueprint, flash, make_response, redirect, render_template,
    request, url_for, Response, send_file
)
from flask_login import current_user, login_required
from sqlalchemy import distinct
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from models import College, Course, Result, User, db

grades_bp = Blueprint("grades_bp", __name__, template_folder="templates")

# ===========================
# Helper - Calculate Grade
# ===========================
def calculate_grade(marks, out_of=100):
    try:
        marks = int(marks)
        percent = (marks / int(out_of)) * 100 if out_of else 0
        if percent >= 90:
            return "A+", 10.0
        elif percent >= 80:
            return "A", 9.0
        elif percent >= 70:
            return "B+", 8.0
        elif percent >= 60:
            return "B", 7.0
        elif percent >= 50:
            return "C", 6.0
        elif percent >= 40:
            return "D", 5.0
        else:
            return "F", 0.0
    except (ValueError, TypeError):
        return "N/A", 0.0

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

    query = Result.query.filter_by(student_id=current_user.id, approved_by_admin=True)
    if selected_semester:
        query = query.filter(Result.semester == selected_semester)

    results = query.all()

    semesters_query = (
        db.session.query(distinct(Result.semester))
        .filter_by(student_id=current_user.id)
        .all()
    )
    semesters = sorted([s[0] for s in semesters_query], reverse=True)

    return render_template(
        "student_grades.html",
        results=results,
        semesters=semesters,
        selected_semester=selected_semester,
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
    query = Result.query.filter_by(student_id=current_user.id, approved_by_admin=True)
    if selected_semester:
        query = query.filter(Result.semester == selected_semester)
    results = query.all()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(
        width / 2,
        height - 50,
        current_user.college.name if current_user.college else "My College",
    )

    # Student Info
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 120, f"Name: {current_user.name}")
    pdf.drawString(50, height - 140, f"Enrollment No: {current_user.enrollment_no or 'N/A'}")
    pdf.drawString(50, height - 160, f"Program: {current_user.program or 'N/A'}")
    pdf.drawString(50, height - 180, f"Semester: {selected_semester or 'All'}")
    pdf.drawString(50, height - 200, f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")

    # Table
    pdf.setFont("Helvetica-Bold", 11)
    y = height - 240
    pdf.drawString(50, y, "Course Code")
    pdf.drawString(150, y, "Course Name")
    pdf.drawString(350, y, "Marks")
    pdf.drawString(420, y, "Grade")
    y -= 20

    pdf.setFont("Helvetica", 11)
    for r in results:
        pdf.drawString(50, y, r.course.course_code if r.course else "-")
        pdf.drawString(150, y, r.course.course_name if r.course else "-")
        pdf.drawString(350, y, str(r.marks))
        pdf.drawString(420, y, r.grade)
        y -= 20
        if y < 100:
            pdf.showPage()
            y = height - 100

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=grades_{current_user.id}.pdf"
    return response

# ===========================
# Faculty Upload Grades
# ===========================
@grades_bp.route("/faculty/grades/upload", methods=["GET", "POST"])
@login_required
def faculty_upload_grades():
    if current_user.role != "Faculty":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        student_id = request.form.get("student_id")
        course_id = request.form.get("course_id")
        semester = request.form.get("semester")
        marks = request.form.get("marks")
        out_of = request.form.get("out_of", 100)
        credits = request.form.get("credits", 4)

        if not all([student_id, course_id, semester, marks]):
            flash("Please fill all required fields", "danger")
            return redirect(url_for("grades_bp.faculty_upload_grades"))

        grade, grade_point = calculate_grade(marks, out_of)

        result = Result(
            student_id=student_id,
            course_id=course_id,
            semester=semester,
            marks=int(marks),
            out_of=int(out_of),
            credits=int(credits),
            grade=grade,
            grade_point=grade_point,
            approved_by_admin=False,
        )
        db.session.add(result)
        db.session.commit()
        flash("✅ Result uploaded successfully (pending admin approval)", "success")
        return redirect(url_for("grades_bp.faculty_upload_grades"))

    students = User.query.filter_by(role="Student").all()
    courses = Course.query.all()
    semesters = db.session.query(distinct(User.semester)).filter(User.semester.isnot(None)).all()
    semesters = [s[0] for s in semesters]

    return render_template("faculty_grades_upload.html", students=students, courses=courses, semesters=semesters)

# ===========================
# Admin Approve Results
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

# ===========================
# Faculty View + Edit Results
# ===========================
@grades_bp.route("/faculty/grades/view", methods=["GET", "POST"])
@login_required
def faculty_view_grades():
    if current_user.role != "Faculty":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.index"))

    # Handle edits
    if request.method == "POST":
        result_id = request.form.get("result_id")
        marks = request.form.get("marks")
        out_of = request.form.get("out_of")
        credits = request.form.get("credits")

        result = db.session.get(Result, int(result_id))
        if result and not result.approved_by_admin:
            result.marks = int(marks)
            result.out_of = int(out_of)
            result.credits = int(credits)
            grade, grade_point = calculate_grade(result.marks, result.out_of)
            result.grade = grade
            result.grade_point = grade_point
            db.session.commit()
            flash("✅ Result updated successfully", "success")
        else:
            flash("❌ Cannot edit approved results", "danger")

        return redirect(url_for("grades_bp.faculty_view_grades"))

    course_id = request.args.get("course_id")
    semester = request.args.get("semester")

    query = Result.query.join(Course).join(User)
    if course_id:
        query = query.filter(Result.course_id == course_id)
    if semester:
        query = query.filter(Result.semester == semester)

    results = query.order_by(Result.created_at.desc()).all()
    courses = Course.query.all()
    semesters = db.session.query(distinct(Result.semester)).all()
    semesters = [s[0] for s in semesters]

    return render_template("faculty_view_results.html", results=results, courses=courses, semesters=semesters, selected_course=course_id, selected_semester=semester)

# ===========================
# CSV Export
# ===========================
@grades_bp.route("/faculty/grades/export/csv")
@login_required
def export_grades_csv():
    if current_user.role != "Faculty":
        return redirect(url_for("main.index"))

    course_id = request.args.get("course_id")
    semester = request.args.get("semester")
    query = Result.query
    if course_id:
        query = query.filter(Result.course_id == course_id)
    if semester:
        query = query.filter(Result.semester == semester)

    results = query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student", "Course Code", "Course Name", "Semester",
                     "Marks", "Out Of", "Credits", "Grade", "Grade Point", "Approved"])
    for r in results:
        writer.writerow([
            r.student.name,
            r.course.course_code,
            r.course.course_name,
            r.semester,
            r.marks,
            r.out_of,
            r.credits,
            r.grade,
            r.grade_point,
            "Yes" if r.approved_by_admin else "No"
        ])

    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=grades.csv"})

# ===========================
# Excel Export
# ===========================
@grades_bp.route("/faculty/grades/export/xlsx")
@login_required
def export_grades_xlsx():
    if current_user.role != "Faculty":
        return redirect(url_for("main.index"))

    course_id = request.args.get("course_id")
    semester = request.args.get("semester")
    query = Result.query
    if course_id:
        query = query.filter(Result.course_id == course_id)
    if semester:
        query = query.filter(Result.semester == semester)

    results = query.all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Grades"

    headers = ["Student", "Course Code", "Course Name", "Semester",
               "Marks", "Out Of", "Credits", "Grade", "Grade Point", "Approved"]
    ws.append(headers)

    for r in results:
        ws.append([
            r.student.name,
            r.course.course_code,
            r.course.course_name,
            r.semester,
            r.marks,
            r.out_of,
            r.credits,
            r.grade,
            r.grade_point,
            "Yes" if r.approved_by_admin else "No"
        ])

    for col in ws.columns:
        length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = length + 3

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="grades.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
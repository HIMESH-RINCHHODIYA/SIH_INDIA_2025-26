import io
import csv
import os
import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, current_app
from werkzeug.utils import secure_filename
from extensions import db
from models import User, FeeConfig, FeePayment, College
from flask_login import login_required, current_user
from sqlalchemy import distinct
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

admin_fee = Blueprint("admin_fee", __name__, url_prefix="/admin/fees")

# ============================
# Admin Fee Dashboard (HTML page)
# ============================
@admin_fee.route("/", methods=["GET"])
@login_required
def admin_fees():
    if current_user.role != "Admin":
        flash("Unauthorized", "danger")
        return redirect(url_for("student_fee.student_fees"))
    return render_template("admin_fees.html")


# ============================
# Upload/Update College Info (Name + Logo)
# ============================
@admin_fee.route("/api/college", methods=["POST"])
@login_required
def update_college():
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    name = request.form.get("name")
    logo_file = request.files.get("logo")

    if not name:
        return jsonify({"error": "College name required"}), 400

    # Get or create college
    college = College.query.first()
    if not college:
        college = College(name=name)
        db.session.add(college)
    else:
        college.name = name

    # Handle logo upload
    if logo_file:
        filename = secure_filename(logo_file.filename)
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        logo_file.save(filepath)
        college.logo = filepath

    db.session.commit()
    return jsonify({"message": "College updated successfully!"})


# ============================
# Dropdown values API
# ============================
@admin_fee.route("/api/dropdowns")
@login_required
def dropdowns_api():
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    programs = [p[0] for p in db.session.query(distinct(User.program)).filter(User.program.isnot(None)).all()]
    branches = [b[0] for b in db.session.query(distinct(User.branch)).filter(User.branch.isnot(None)).all()]
    years = [y[0] for y in db.session.query(distinct(User.year)).filter(User.year.isnot(None)).all()]

    return jsonify({"programs": programs, "branches": branches, "years": years})


# ============================
# Save Fee Configuration API
# ============================
@admin_fee.route("/api/save_fee_config", methods=["POST"])
@login_required
def save_fee_config():
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    program = data.get("program")
    branch = data.get("branch")
    year = data.get("year")
    amount = data.get("amount")
    last_date = data.get("last_date")

    if not all([program, branch, year, amount]):
        return jsonify({"error": "All fields required"}), 400

    try:
        fee_config = FeeConfig(
            program=program,
            branch=branch,
            year=year,
            amount=Decimal(amount),
            last_date=datetime.datetime.strptime(last_date, "%Y-%m-%d").date() if last_date else None,
        )
        db.session.add(fee_config)
        db.session.commit()
        return jsonify({"message": "Fee config saved!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================
# Fetch Students API (with fee info)
# ============================
@admin_fee.route("/api/students")
@login_required
def students_api():
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    program = request.args.get("program") or None
    branch = request.args.get("branch") or None
    year = request.args.get("year") or None

    query = User.query.filter_by(role="Student")
    if program:
        query = query.filter_by(program=program)
    if branch:
        query = query.filter_by(branch=branch)
    if year:
        query = query.filter_by(year=year)

    students = []
    for s in query.all():
        cfg = FeeConfig.query.filter_by(program=s.program, branch=s.branch, year=s.year).order_by(FeeConfig.id.desc()).first()
        payments = FeePayment.query.filter_by(student_id=s.id).all()
        paid_amount = sum(float(p.amount) for p in payments if p.status == "Paid")
        status = "Unpaid"
        if paid_amount > 0 and cfg and paid_amount < float(cfg.amount):
            status = "Pending"
        elif cfg and paid_amount >= float(cfg.amount):
            status = "Paid"

        students.append({
            "id": s.id,
            "name": s.name,
            "email": s.email,
            "program": s.program,
            "branch": s.branch,
            "year": s.year,
            "applied_fee": {"amount": float(cfg.amount)} if cfg else None,
            "paid_amount": paid_amount,
            "status": status
        })

    return jsonify(students)


# ============================
# Generate & Download Student Fee Receipt
# ============================
@admin_fee.route("/receipt/<int:student_id>")
@login_required
def generate_receipt(student_id):
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    student = User.query.get_or_404(student_id)
    college = student.college or College.query.first()
    payments = FeePayment.query.filter_by(student_id=student.id, status="Paid").all()
    total_paid = sum(float(p.amount) for p in payments)

    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    y = height - 50

    # College Logo & Name
    if college and college.logo and os.path.exists(college.logo):
        pdf.drawImage(college.logo, 40, y - 60, width=80, height=60, preserveAspectRatio=True, mask="auto")
    if college:
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(140, y - 20, college.name)

    # Student info
    y -= 100
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, y, f"Student Name: {student.name}")
    pdf.drawString(50, y - 20, f"Roll No: {student.roll_no}")
    pdf.drawString(50, y - 40, f"Program: {student.program} | Branch: {student.branch} | Year: {student.year}")
    pdf.drawString(50, y - 60, f"Email: {student.email}")

    # Fee details
    y -= 100
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Fee Payment Summary")

    y -= 30
    pdf.setFont("Helvetica", 12)
    for p in payments:
        pdf.drawString(60, y, f"Payment ID: {p.payment_id} | Amount: {float(p.amount)} | Date: {p.created_at.strftime('%Y-%m-%d')}")
        y -= 20

    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, f"Total Paid: {total_paid}")

    pdf.save()
    output.seek(0)
    return send_file(output, mimetype="application/pdf", as_attachment=True, download_name=f"receipt_{student.roll_no}.pdf")


# ============================
# Download students list (CSV / PDF)
# ============================
@admin_fee.route("/download_students/<filetype>")
@login_required
def download_students(filetype):
    if current_user.role != "Admin":
        flash("Unauthorized", "danger")
        return redirect(url_for("student_fee.student_fees"))

    program_filter = request.args.get("program") or ""
    branch_filter = request.args.get("branch") or ""
    year_filter = request.args.get("year") or ""

    query = User.query.filter_by(role="Student")
    if program_filter:
        query = query.filter_by(program=program_filter)
    if branch_filter:
        query = query.filter_by(branch=branch_filter)
    if year_filter:
        query = query.filter_by(year=year_filter)

    students = query.all()

    if filetype.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "Email", "Roll No", "Program", "Branch", "Year"])
        for s in students:
            writer.writerow([s.name, s.email, s.roll_no, s.program, s.branch, s.year])
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="students.csv")

    elif filetype.lower() == "pdf":
        output = io.BytesIO()
        pdf = canvas.Canvas(output, pagesize=A4)
        pdf.setFont("Helvetica", 10)
        y = 800
        pdf.drawString(50, y, "Students List")
        y -= 20
        for s in students:
            pdf.drawString(50, y, f"{s.name} | {s.email} | {s.roll_no} | {s.program} | {s.branch} | {s.year}")
            y -= 15
            if y < 50:
                pdf.showPage()
                y = 800
        pdf.save()
        output.seek(0)
        return send_file(output, mimetype="application/pdf", as_attachment=True, download_name="students.pdf")

    flash("Invalid file type!", "danger")
    return redirect(url_for("admin_fee.admin_fees"))

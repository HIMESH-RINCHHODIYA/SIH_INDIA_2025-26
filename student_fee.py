import datetime
import io
import os
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, send_file
from flask_login import login_required, current_user
from extensions import db
from models import FeePayment, FeeConfig, College

student_fee_bp = Blueprint("student_fee", __name__, url_prefix="/student/fees")

# ============================
# Student Side
# ============================

@student_fee_bp.route("/")
@login_required
def student_fees():
    """Student view of their fee records, current fee config, and dues"""
    payments = FeePayment.query.filter_by(student_id=current_user.id).order_by(FeePayment.created_at.desc()).all()

    fee_config = FeeConfig.query.filter_by(
        program=current_user.program.strip().upper() if current_user.program else None,
        branch=current_user.branch.strip().upper() if current_user.branch else None,
        year=str(current_user.year).strip() if current_user.year else None
    ).order_by(FeeConfig.updated_at.desc()).first()

    total_paid = sum(float(p.amount) for p in payments if p.status == "Paid")

    if not fee_config:
        return render_template(
            "student_fees.html",
            payments=payments,
            fee_config=None,
            total_paid=total_paid,
            dues=None,
            error_msg="⚠️ Fee configuration has not been set by the admin for your program/branch/year."
        )

    total_fee = float(fee_config.amount)
    dues = max(total_fee - total_paid, 0)

    return render_template(
        "student_fees.html",
        payments=payments,
        fee_config=fee_config,
        total_paid=total_paid,
        dues=dues,
        error_msg=None
    )


@student_fee_bp.route("/create", methods=["POST"])
@login_required
def create_fee():
    """Student initiates a fee payment (UPI / NetBanking)"""
    fee_config = FeeConfig.query.filter_by(
        program=current_user.program,
        branch=current_user.branch,
        year=current_user.year
    ).order_by(FeeConfig.updated_at.desc()).first()

    if not fee_config:
        return jsonify({"error": "Fee configuration not set by admin"}), 400

    payments = FeePayment.query.filter_by(student_id=current_user.id).all()
    total_paid = sum(float(p.amount) for p in payments if p.status == "Paid")
    dues = max(float(fee_config.amount) - total_paid, 0)

    if dues <= 0:
        return jsonify({"error": "No dues pending"}), 400

    amount = request.form.get("amount", type=Decimal, default=Decimal(dues))
    method = request.form.get("method", "UPI")

    if not amount or amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    if float(amount) > dues:
        amount = Decimal(dues)

    new_payment = FeePayment(
        student_id=current_user.id,
        college_id=current_user.college_id,
        amount=float(amount),
        status="Pending",
        payment_method=method,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.session.add(new_payment)
    db.session.commit()

    if method == "UPI":
        upi_id = "9685527886@ybl"
        payee_name = "College Fees"
        note = f"Fee Payment - {current_user.name}"
        upi_url = f"upi://pay?pa={upi_id}&pn={payee_name}&am={amount}&cu=INR&tn={note}"
        return jsonify({"method": "UPI", "upi_url": upi_url})

    elif method == "NetBanking":
        redirect_url = url_for("student_fee.mock_netbanking", payment_id=new_payment.id, _external=True)
        return jsonify({"method": "NetBanking", "redirect_url": redirect_url})

    return jsonify({"error": "Unsupported payment method"}), 400


@student_fee_bp.route("/mock_netbanking/<int:payment_id>")
@login_required
def mock_netbanking(payment_id):
    """Simulate a NetBanking flow: mark payment as Paid"""
    payment = FeePayment.query.get_or_404(payment_id)
    if payment.student_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("student_fee.student_fees"))

    payment.status = "Paid"
    payment.updated_at = datetime.datetime.utcnow()
    db.session.commit()

    flash("✅ NetBanking payment successful!", "success")
    return redirect(url_for("student_fee.student_fees"))


@student_fee_bp.route("/receipt/<int:payment_id>")
@login_required
def download_receipt(payment_id):
    """Download PDF receipt for a specific payment"""
    payment = FeePayment.query.get_or_404(payment_id)
    if payment.student_id != current_user.id and current_user.role != "Admin":
        flash("Unauthorized", "danger")
        return redirect(url_for("student_fee.student_fees"))

    college = payment.college or College.query.first()
    student = payment.student

    output = io.BytesIO()
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 50

    if college and college.logo and os.path.exists(college.logo):
        pdf.drawImage(college.logo, 40, y - 60, width=80, height=60, preserveAspectRatio=True, mask="auto")
    if college:
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(140, y - 20, college.name)

    y -= 100
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, y, f"Student Name: {student.name}")
    pdf.drawString(50, y - 20, f"Roll No: {student.roll_no}")
    pdf.drawString(50, y - 40, f"Program: {student.program} | Branch: {student.branch} | Year: {student.year}")
    pdf.drawString(50, y - 60, f"Email: {student.email}")

    y -= 100
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Fee Payment Receipt")

    y -= 30
    pdf.setFont("Helvetica", 12)
    pdf.drawString(60, y, f"Payment ID: {payment.id}")
    pdf.drawString(60, y - 20, f"Method: {payment.payment_method}")
    pdf.drawString(60, y - 40, f"Amount: {payment.amount}")
    pdf.drawString(60, y - 60, f"Status: {payment.status}")
    pdf.drawString(60, y - 80, f"Date: {payment.created_at.strftime('%Y-%m-%d')}")

    pdf.save()
    output.seek(0)
    return send_file(output, mimetype="application/pdf", as_attachment=True, download_name=f"receipt_{student.roll_no}.pdf")


# ============================
# Admin Side
# ============================

@student_fee_bp.route("/admin", methods=["GET"])
@login_required
def admin_fee_dashboard():
    if current_user.role != "Admin":
        flash("Unauthorized access", "danger")
        return redirect(url_for("student_fee.student_fees"))

    payments = FeePayment.query.order_by(FeePayment.updated_at.desc()).all()
    configs = FeeConfig.query.order_by(FeeConfig.updated_at.desc()).all()
    return render_template("admin_fee.html", payments=payments, configs=configs)


@student_fee_bp.route("/admin/config", methods=["POST"])
@login_required
def admin_fee_config():
    if current_user.role != "Admin":
        flash("Unauthorized", "danger")
        return redirect(url_for("student_fee.student_fees"))

    program = request.form.get("program", "").strip().upper()
    branch = request.form.get("branch", "").strip().upper()
    year = request.form.get("year", "").strip()
    amount = request.form.get("amount", type=Decimal)
    last_date = request.form.get("last_date")

    if not program or not branch or not year or not amount or not last_date:
        flash("All fields are required", "danger")
        return redirect(url_for("student_fee.admin_fee_dashboard"))

    config = FeeConfig(
        program=program,
        branch=branch,
        year=year,
        amount=float(amount),
        last_date=datetime.datetime.strptime(last_date, "%Y-%m-%d").date(),
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.session.add(config)
    db.session.commit()

    flash("✅ Fee configuration saved successfully", "success")
    return redirect(url_for("student_fee.admin_fee_dashboard"))


@student_fee_bp.route("/admin/update/<int:payment_id>", methods=["POST"])
@login_required
def admin_update_payment(payment_id):
    if current_user.role != "Admin":
        flash("Unauthorized", "danger")
        return redirect(url_for("student_fee.student_fees"))

    payment = FeePayment.query.get_or_404(payment_id)
    new_status = request.form.get("status")

    if new_status not in ["Unpaid", "Pending", "Paid", "Failed"]:
        flash("Invalid status", "danger")
        return redirect(url_for("student_fee.admin_fee_dashboard"))

    payment.status = new_status
    payment.updated_at = datetime.datetime.utcnow()
    db.session.commit()

    flash("✅ Payment status updated", "success")
    return redirect(url_for("student_fee.admin_fee_dashboard"))

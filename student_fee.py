import datetime
import io
from decimal import Decimal

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, send_file, url_for)
from flask_login import current_user, login_required

from extensions import db
from hostel_models import HostelAllocation
from models import College, FeeConfig, FeePayment, InstitutionAccount

student_fee_bp = Blueprint("student_fee", __name__, url_prefix="/student/fees")


# -------------------------------------------------------
# STUDENT DASHBOARD
# -------------------------------------------------------
@student_fee_bp.route("/")
@login_required
def student_fees():
    payments = (
        FeePayment.query.filter_by(student_id=current_user.id)
        .order_by(FeePayment.created_at.desc())
        .all()
    )

    def fetch_config(ftype):
        return (
            FeeConfig.query.filter_by(
                program=(
                    current_user.program.strip().upper()
                    if current_user.program
                    else None
                ),
                branch=(
                    current_user.branch.strip().upper() if current_user.branch else None
                ),
                year=str(current_user.year).strip() if current_user.year else None,
                fee_type=ftype,
            )
            .order_by(FeeConfig.updated_at.desc())
            .first()
        )

    # Academic
    academic_cfg = fetch_config("ACADEMIC")
    academic_paid = sum(
        float(p.amount)
        for p in payments
        if p.status == "Paid" and p.fee_type == "ACADEMIC"
    )
    academic_due = max(
        (float(academic_cfg.amount) if academic_cfg else 0) - academic_paid, 0
    )

    # Hostel allocation check
    allocation = HostelAllocation.query.filter_by(
        student_id=current_user.id, status="Active"
    ).first()
    hostel_cfg = fetch_config("HOSTEL") if allocation else None
    hostel_paid = sum(
        float(p.amount)
        for p in payments
        if p.status == "Paid" and p.fee_type == "HOSTEL"
    )
    hostel_due = (
        max((float(hostel_cfg.amount) if hostel_cfg else 0) - hostel_paid, 0)
        if hostel_cfg
        else 0
    )

    return render_template(
        "student_fees.html",
        payments=payments,
        academic_config=academic_cfg,
        academic_paid=academic_paid,
        academic_due=academic_due,
        hostel_config=hostel_cfg,
        hostel_paid=hostel_paid,
        hostel_due=hostel_due,
        hostel_allowed=allocation is not None,
    )


# -------------------------------------------------------
# STUDENT CREATES PAYMENT
# -------------------------------------------------------
@student_fee_bp.route("/create", methods=["POST"])
@login_required
def create_fee():
    fee_type = request.form.get("fee_type", "ACADEMIC")
    amount = request.form.get("amount", type=Decimal)

    # Find default account for this fee type
    account = InstitutionAccount.query.filter_by(
        fee_type=fee_type, is_default=True
    ).first()
    if not account:
        return jsonify({"error": "No collection account set for this fee type"}), 400

    payment = FeePayment(
        student_id=current_user.id,
        college_id=current_user.college_id,
        amount=float(amount),
        status="Pending",
        fee_type=fee_type,
        account_id=account.id,
    )
    db.session.add(payment)
    db.session.commit()

    if account.account_type == "UPI":
        # Generate UPI deep link
        upi_url = f"upi://pay?pa={account.upi_id}&pn={account.account_name}&am={payment.amount}&cu=INR&tn=Fee-{fee_type}"
        return jsonify({"method": "UPI", "upi_url": upi_url})

    elif account.account_type == "PAYU":
        return redirect(url_for("student_fee.pay_payu", payment_id=payment.id))

    elif account.account_type == "HDFC":
        return redirect(url_for("student_fee.pay_hdfc", payment_id=payment.id))

    return jsonify({"error": "Unsupported Payment Gateway"}), 400


@student_fee_bp.route("/mock_netbanking/<int:payment_id>")
@login_required
def mock_netbanking(payment_id):
    pay = FeePayment.query.get_or_404(payment_id)
    if pay.student_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("student_fee.student_fees"))
    pay.status = "Paid"
    pay.updated_at = datetime.datetime.utcnow()
    db.session.commit()
    flash("✅ NetBanking payment successful!", "success")
    return redirect(url_for("student_fee.student_fees"))


@student_fee_bp.route("/receipt/<int:payment_id>")
@login_required
def receipt(payment_id):
    pay = FeePayment.query.get_or_404(payment_id)
    if pay.student_id != current_user.id and current_user.role != "Admin":
        flash("Unauthorized", "danger")
        return redirect(url_for("student_fee.student_fees"))

    college = pay.college or College.query.first()
    student = pay.student
    output = io.BytesIO()
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(output, pagesize=A4)
    y = A4[1] - 50
    if college and college.name:
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(140, y - 20, college.name)
    y -= 100
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Fee Receipt")
    y -= 30
    pdf.setFont("Helvetica", 12)
    pdf.drawString(60, y, f"Fee Type: {pay.fee_type}")
    pdf.drawString(60, y - 20, f"Amount: ₹{pay.amount}")
    pdf.drawString(60, y - 40, f"Method: {pay.payment_method}")
    pdf.drawString(60, y - 60, f"Status: {pay.status}")
    pdf.drawString(60, y - 80, f"Date: {pay.created_at.strftime('%Y-%m-%d')}")
    pdf.save()
    output.seek(0)
    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"receipt_{student.roll_no}.pdf",
    )

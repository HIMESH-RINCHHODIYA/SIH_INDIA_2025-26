import datetime

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from extensions import db
from hostel_models import HostelAllocation
from models import FeeConfig, FeePayment, InstitutionAccount, User

admin_fee_bp = Blueprint("admin_fee", __name__, url_prefix="/admin/fees")


# -------------------------------------------------------
# ADMIN DASHBOARD
# -------------------------------------------------------
@admin_fee_bp.route("/")
@login_required
def admin_fee_dashboard():
    if current_user.role != "Admin":
        flash("Unauthorized", "danger")
        return redirect(
            url_for("student_fee.student_fees")
        )  # student fallback if not admin
    payments = FeePayment.query.order_by(FeePayment.updated_at.desc()).all()
    configs = FeeConfig.query.order_by(FeeConfig.updated_at.desc()).all()
    return render_template("admin_fee.html", payments=payments, configs=configs)


# -------------------------------------------------------
# DROPDOWN VALUES
# -------------------------------------------------------
@admin_fee_bp.route("/api/dropdowns")
@login_required
def dropdowns():
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    progs = sorted(
        {
            u.program
            for u in User.query.filter(User.role == "Student", User.program != None)
        }
    )
    branches = sorted(
        {
            u.branch
            for u in User.query.filter(User.role == "Student", User.branch != None)
        }
    )
    years = sorted(
        {u.year for u in User.query.filter(User.role == "Student", User.year != None)}
    )
    return jsonify({"programs": progs, "branches": branches, "years": years})


# -------------------------------------------------------
# SAVE CONFIG
# -------------------------------------------------------
@admin_fee_bp.route("/api/save_fee_config", methods=["POST"])
@login_required
def save_fee_config():
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json()
    try:
        cfg = FeeConfig(
            program=data.get("program", "").upper(),
            branch=data.get("branch", "").upper(),
            year=data.get("year", ""),
            amount=float(data.get("amount")),
            last_date=datetime.datetime.strptime(data["last_date"], "%Y-%m-%d").date(),
            fee_type=data.get("fee_type", "ACADEMIC").upper(),
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        db.session.add(cfg)
        db.session.commit()
        return jsonify({"message": f"{cfg.fee_type} config saved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------
# STUDENT LIST
# -------------------------------------------------------
@admin_fee_bp.route("/api/students")
@login_required
def students():
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    mode = request.args.get("mode", "academic")  # "academic" or "hostel"
    program = request.args.get("program")
    branch = request.args.get("branch")
    year = request.args.get("year")
    hostel_id = request.args.get("hostel_id")

    students = []
    if mode == "academic":
        # Default Academic filter
        query = User.query.filter_by(role="Student")
        if program:
            query = query.filter(User.program == program)
        if branch:
            query = query.filter(User.branch == branch)
        if year:
            query = query.filter(User.year == year)
        students = query.all()

    elif mode == "hostel":
        # Hostel filter mode
        query = HostelAllocation.query.filter_by(status="Active")
        if hostel_id:  # filter by selected hostel
            query = query.filter(HostelAllocation.hostel_id == int(hostel_id))
        allocations = query.all()
        students = [a.student for a in allocations]

    # Build result
    result = []
    for st in students:

        def stats(ftype):
            cfg = (
                FeeConfig.query.filter_by(
                    program=st.program.upper() if st.program else None,
                    branch=st.branch.upper() if st.branch else None,
                    year=st.year,
                    fee_type=ftype,
                )
                .order_by(FeeConfig.updated_at.desc())
                .first()
            )
            applied = float(cfg.amount) if cfg else 0
            paid = sum(
                float(p.amount)
                for p in st.fee_payments
                if p.status == "Paid" and p.fee_type == ftype
            )
            dues = max(applied - paid, 0)
            return {"applied": applied, "paid": paid, "dues": dues}

        result.append(
            {
                "id": st.id,
                "name": st.name,
                "email": st.email,
                "program": st.program,
                "branch": st.branch,
                "year": st.year,
                "academic_fee": stats("ACADEMIC"),
                "hostel_fee": stats("HOSTEL"),
            }
        )

    return jsonify(result)


@admin_fee_bp.route("/accounts", methods=["GET", "POST"])
@login_required
def manage_accounts():
    if current_user.role != "Admin":
        flash("Unauthorized", "danger")
        return redirect(url_for("student_fee.student_fees"))

    if request.method == "POST":
        acc = InstitutionAccount(
            account_name=request.form["account_name"],
            fee_type=request.form["fee_type"],
            account_type=request.form["account_type"],
            merchant_id=request.form.get("merchant_id"),
            api_key=request.form.get("api_key"),
            api_secret=request.form.get("api_secret"),
            salt=request.form.get("salt"),
            upi_id=request.form.get("upi_id"),
            is_default=("is_default" in request.form),
        )

        if acc.is_default:
            # Reset any other default for this fee_type
            InstitutionAccount.query.filter_by(fee_type=acc.fee_type).update(
                {"is_default": False}
            )

        db.session.add(acc)
        db.session.commit()
        flash("✅ Collection account saved.", "success")
        return redirect(url_for("admin_fee.manage_accounts"))

    accounts = InstitutionAccount.query.all()
    return render_template("admin_accounts.html", accounts=accounts)


@admin_fee_bp.route("/reports")
@login_required
def reports():
    if current_user.role != "Admin":
        return "Unauthorized", 403
    by_fee_type = (
        db.session.query(
            FeePayment.fee_type,
            db.func.count(FeePayment.id),
            db.func.sum(FeePayment.amount),
        )
        .group_by(FeePayment.fee_type)
        .all()
    )
    by_account = (
        db.session.query(
            InstitutionAccount.account_name,
            InstitutionAccount.account_type,
            FeePayment.status,
            db.func.count(FeePayment.id),
            db.func.sum(FeePayment.amount),
        )
        .join(FeePayment, InstitutionAccount.id == FeePayment.account_id)
        .group_by(InstitutionAccount.account_name, FeePayment.status)
        .all()
    )
    return render_template(
        "admin_reports.html", by_fee_type=by_fee_type, by_account=by_account
    )


# -------------------------------------------------------
# PAYMENT HISTORY
# -------------------------------------------------------
@admin_fee_bp.route("/api/payments/<int:sid>")
@login_required
def payments(sid):
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    st = User.query.get_or_404(sid)
    return jsonify(
        [
            {
                "id": p.id,
                "amount": float(p.amount),
                "status": p.status,
                "created_at": p.created_at.strftime("%Y-%m-%d"),
                "fee_type": p.fee_type,
            }
            for p in st.fee_payments
        ]
    )

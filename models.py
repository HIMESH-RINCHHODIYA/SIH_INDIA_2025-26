# models.py
import hashlib
import json
import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from flask import (Blueprint, current_app, render_template_string, request,
                   url_for)
from flask_login import UserMixin, current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from extensions import db

# ======================================================================
# 1. COLLEGE & ACADEMIC STRUCTURE
# ======================================================================


class College(db.Model):
    __tablename__ = "colleges"
    __table_args__ = (db.UniqueConstraint("name", name="uq_colleges_name"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    domain = db.Column(db.String(150), unique=True, nullable=False)
    logo = db.Column(db.String(250))  # path/url to logo

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    users = db.relationship("User", back_populates="college", lazy="dynamic")
    fee_payments = db.relationship(
        "FeePayment", back_populates="college", lazy="dynamic"
    )

    def __repr__(self):
        return f"<College id={self.id} name={self.name}>"


class Program(db.Model):
    __tablename__ = "programs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    duration_years = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    branches = db.relationship(
        "Branch", back_populates="program", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Program id={self.id} name={self.name}>"


class Branch(db.Model):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    program = db.relationship("Program", back_populates="branches")

    def __repr__(self):
        return f"<Branch id={self.id} name={self.name} program_id={self.program_id}>"


class Year(db.Model):
    __tablename__ = "years"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    def __repr__(self):
        return f"<Year id={self.id} name={self.name}>"


class Semester(db.Model):
    __tablename__ = "semesters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    def __repr__(self):
        return f"<Semester id={self.id} name={self.name}>"


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(150), nullable=False, unique=True)
    course_code = db.Column(db.String(50), nullable=False, unique=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    attendance_records = db.relationship("Attendance", back_populates="course")
    faculty_courses = db.relationship("FacultyCourse", back_populates="course")
    student_enrollments = db.relationship("StudentCourse", back_populates="course")
    results = db.relationship("Result", back_populates="course")

    def __repr__(self):
        return f"<Course id={self.id} code={self.course_code} name={self.course_name}>"


# ======================================================================
# 2. USER MODEL
# ======================================================================


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True)

    # Login/Auth
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), default="Student")
    verified = db.Column(db.Boolean, default=False)

    # Academic Info
    enrollment_no = db.Column(db.String(50), unique=True)
    scholar_no = db.Column(db.String(50))
    roll_no = db.Column(db.String(50), unique=True)
    program = db.Column(db.String(100))
    year = db.Column(db.String(10))
    branch = db.Column(db.String(100))
    section = db.Column(db.String(20))
    semester = db.Column(db.String(20))
    class_name = db.Column(db.String(100))
    admission_date = db.Column(db.Date)

    # Personal Info
    dob = db.Column(db.Date)
    gender = db.Column(db.String(20))
    nationality = db.Column(db.String(50))
    religion = db.Column(db.String(50))
    aadhaar_no = db.Column(db.String(20))
    blood_group = db.Column(db.String(5))
    contact = db.Column(db.String(20))
    mother_tongue = db.Column(db.String(50))
    marital_status = db.Column(db.String(20), default="Single")
    samagra_id = db.Column(db.String(50))
    category = db.Column(db.String(50))
    domicile_state = db.Column(db.String(50))

    # Parents Info
    father_name = db.Column(db.String(150))
    father_name_hindi = db.Column(db.String(150))
    father_mobile = db.Column(db.String(20))
    father_income = db.Column(db.Numeric(12, 2))
    mother_name = db.Column(db.String(150))
    mother_name_hindi = db.Column(db.String(150))
    mother_mobile = db.Column(db.String(20))
    mother_income = db.Column(db.Numeric(12, 2))

    # Address
    permanent_address = db.Column(db.Text)
    permanent_city = db.Column(db.String(100))
    permanent_state = db.Column(db.String(100))
    permanent_pin = db.Column(db.String(20))
    local_address = db.Column(db.Text)
    local_city = db.Column(db.String(100))
    local_state = db.Column(db.String(100))
    local_pin = db.Column(db.String(20))

    # Bank Details
    bank_name = db.Column(db.String(100))
    bank_branch = db.Column(db.String(100))
    bank_account_no = db.Column(db.String(50))
    bank_ifsc = db.Column(db.String(20))

    # File uploads
    photo = db.Column(db.String(200))
    id_card = db.Column(db.String(200))
    certificate = db.Column(db.String(200))
    transcript = db.Column(db.String(200))
    signature = db.Column(db.String(200))

    # Relationships
    college = db.relationship("College", back_populates="users")
    attendance_records = db.relationship(
        "Attendance",
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    fee_payments = db.relationship(
        "FeePayment",
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    results = db.relationship(
        "Result", back_populates="student", cascade="all, delete-orphan", lazy="dynamic"
    )
    student_courses = db.relationship(
        "StudentCourse", back_populates="student", lazy="dynamic"
    )
    faculty_courses = db.relationship(
        "FacultyCourse", back_populates="faculty", lazy="dynamic"
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"


# ======================================================================
# 3. ACADEMIC RECORD MODELS
# ======================================================================
class Result(db.Model):
    __tablename__ = "results"
    __table_args__ = (db.Index("ix_results_student_semester", "student_id", "semester"),)

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    semester = db.Column(db.String(10), nullable=False)

    marks = db.Column(db.Integer, nullable=False)
    out_of = db.Column(db.Integer, default=100)
    credits = db.Column(db.Integer, default=4)
    grade = db.Column(db.String(5), nullable=False)
    grade_point = db.Column(db.Float, default=0.0)

    approved_by_admin = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow, nullable=False)

    student = db.relationship("User", back_populates="results")
    course = db.relationship("Course", back_populates="results")

    def __repr__(self):
        return f"<Result student={self.student_id} course={self.course_id} marks={self.marks} grade={self.grade}>"


class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    branch = db.Column(db.String(50), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # Present/Absent
    remarks = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("User", back_populates="attendance_records")
    course = db.relationship("Course", back_populates="attendance_records")

    def __repr__(self):
        return f"<Attendance student={self.student_id} course={self.course_id} date={self.date} status={self.status}>"


class StudentCourse(db.Model):
    __tablename__ = "student_courses"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)

    program = db.Column(db.String(100))
    branch = db.Column(db.String(100))
    year = db.Column(db.String(10))
    semester = db.Column(db.String(20))

    student = db.relationship("User", back_populates="student_courses")
    course = db.relationship("Course", back_populates="student_enrollments")

    def __repr__(self):
        return f"<StudentCourse id={self.id} student_id={self.student_id} course_id={self.course_id} semester={self.semester}>"


class FacultyCourse(db.Model):
    __tablename__ = "faculty_courses"

    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)

    program = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(100), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    course_type = db.Column(db.String(20), nullable=False)

    faculty = db.relationship("User", back_populates="faculty_courses")
    course = db.relationship("Course", back_populates="faculty_courses")

    def __repr__(self):
        return f"<FacultyCourse faculty={self.faculty_id} course={self.course_id} sem={self.semester}>"


# ======================================================================
# 4. FEES & CONFIGURATION
# ======================================================================
class FeePayment(db.Model):
    __tablename__ = "fee_payments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"))
    account_id = db.Column(db.Integer, db.ForeignKey("institution_accounts.id"))

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default="Unpaid")
    payment_method = db.Column(db.String(50))
    fee_type = db.Column(db.String(50), default="ACADEMIC")
    order_id = db.Column(db.String(100))
    transaction_id = db.Column(db.String(100))
    response = db.Column(db.Text)
    pg_type = db.Column(db.String(20))  # Added: to store gateway type e.g., PAYU

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    student = db.relationship("User", back_populates="fee_payments")
    college = db.relationship("College", back_populates="fee_payments")
    account = db.relationship("InstitutionAccount", back_populates="payments")

    def __repr__(self):
        return f"<FeePayment {self.fee_type} | {self.amount} via Account {self.account_id}>"


class FeeConfig(db.Model):
    __tablename__ = "fee_configs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    program = db.Column(db.String(100))
    branch = db.Column(db.String(100))
    year = db.Column(db.String(20))
    section = db.Column(db.String(20))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    last_date = db.Column(db.Date)

    # store which type of fee: ACADEMIC / HOSTEL
    fee_type = db.Column(db.String(50), default="ACADEMIC")

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return (
            f"<FeeConfig {self.fee_type} | "
            f"{self.program}/{self.branch}/{self.year}/{self.section} = {self.amount}>"
        )

    # optional: normalize fee_type always uppercase before saving
    def save(self):
        if self.fee_type:
            self.fee_type = self.fee_type.upper()
        db.session.add(self)
        db.session.commit()


# ======================================================================
# 5. DROPDOWN VALUES (Utility Table)
# ======================================================================


class DropdownValue(db.Model):
    __tablename__ = "dropdown_values"
    __table_args__ = (db.UniqueConstraint("field", "value", name="uq_field_value"),)

    id = db.Column(db.Integer, primary_key=True)
    field = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<DropdownValue field={self.field} value={self.value}>"


class InstitutionAccount(db.Model):
    __tablename__ = "institution_accounts"

    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(150), nullable=False)
    fee_type = db.Column(db.String(50), default="ACADEMIC")
    account_type = db.Column(db.String(20))  # HDFC / PAYU / UPI

    # PG credentials
    merchant_id = db.Column(db.String(100))
    api_key = db.Column(db.String(200))
    api_secret = db.Column(db.String(200))
    salt = db.Column(db.String(200))

    upi_id = db.Column(db.String(100))  # optional for UPI payments

    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    payments = db.relationship("FeePayment", back_populates="account")

    def __repr__(self):
        return f"<InstitutionAccount {self.account_name} [{self.account_type}] for {self.fee_type}>"


# ======================================================================
# 6. PAYU INTEGRATION (Blueprint + Routes)
# ======================================================================

student_fee_bp = Blueprint(
    "student_fee", __name__
)  # If you already define this elsewhere, import that instead.


def _format_amount_str(amount) -> str:
    """Return amount as string with exactly 2 decimals, as PayU expects."""
    if isinstance(amount, Decimal):
        dec = amount
    else:
        dec = Decimal(str(amount))
    return format(dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def _build_payu_request_hash(
    key: str,
    salt: str,
    txnid: str,
    amount_str: str,
    productinfo: str,
    firstname: str,
    email: str,
    udfs=None,
) -> str:
    """
    Request hash per PayU: sha512(key|txnid|amount|productinfo|firstname|email|udf1|...|udf10|salt)
    """
    udfs = udfs or [""] * 10
    seq = [key, txnid, amount_str, productinfo, firstname, email] + udfs + [salt]
    hash_str = "|".join(seq)
    return hashlib.sha512(hash_str.encode("utf-8")).hexdigest().lower()


def _build_payu_response_hash(data: dict, salt: str, key: str) -> str:
    """
    Response hash per PayU (reverse hash sequence).
    If 'additionalCharges' present: sha512(additionalCharges|salt|status|udf10|...|udf1|email|firstname|productinfo|amount|txnid|key)
    Else: sha512(salt|status|udf10|...|udf1|email|firstname|productinfo|amount|txnid|key)
    """
    status = data.get("status", "")
    udf_vals = [data.get(f"udf{i}", "") for i in range(1, 11)]
    udf_vals.reverse()  # udf10..udf1

    tail = [
        data.get("email", ""),
        data.get("firstname", ""),
        data.get("productinfo", ""),
        data.get("amount", ""),
        data.get("txnid", ""),
        key,
    ]

    if data.get("additionalCharges"):
        parts = [data.get("additionalCharges"), salt, status] + udf_vals + tail
    else:
        parts = [salt, status] + udf_vals + tail

    hash_str = "|".join(parts)
    return hashlib.sha512(hash_str.encode("utf-8")).hexdigest().lower()


def _validate_payu_response(data: dict, salt: str, key: str) -> bool:
    received = (data.get("hash") or "").lower()
    calculated = _build_payu_response_hash(data, salt, key)
    return received == calculated


@student_fee_bp.route("/pay/payu/<int:payment_id>")
@login_required
def pay_payu(payment_id):
    try:
        payment = FeePayment.query.get_or_404(payment_id)

        # Ensure the logged-in user owns this payment
        if payment.student_id != current_user.id:
            return "Unauthorized", 403

        account = payment.account
        if not account or (account.account_type or "").upper() != "PAYU":
            return "Invalid payment gateway configured", 400

        txnid = str(uuid.uuid4()).replace("-", "")[
            :20
        ]  # PayU allows up to 25; using 20
        productinfo = "College Fee Payment"

        amount_str = _format_amount_str(payment.amount)
        firstname = current_user.name or "Student"
        email = current_user.email or ""
        phone = current_user.contact or ""

        # Build request hash
        req_hash = _build_payu_request_hash(
            key=account.api_key,
            salt=account.salt,
            txnid=txnid,
            amount_str=amount_str,
            productinfo=productinfo,
            firstname=firstname,
            email=email,
            udfs=[""] * 10,
        )

        # Update payment record
        payment.order_id = txnid
        payment.pg_type = "PAYU"
        db.session.commit()

        # PayU endpoint from config, default to test
        payu_url = current_app.config.get(
            "PAYU_PAYMENT_URL", "https://test.payu.in/_payment"
        )

        # Render auto-submit form (Jinja escapes values to minimize XSS risk)
        form_html = render_template_string(
            """
        <!DOCTYPE html>
        <html>
        <head><title>Redirecting…</title></head>
        <body onload="document.getElementById('payuForm').submit();">
            <p>Redirecting to PayU. Please wait…</p>
            <form id="payuForm" action="{{ payu_url }}" method="post">
                <input type="hidden" name="key" value="{{ api_key }}">
                <input type="hidden" name="txnid" value="{{ txnid }}">
                <input type="hidden" name="amount" value="{{ amount }}">
                <input type="hidden" name="productinfo" value="{{ productinfo }}">
                <input type="hidden" name="firstname" value="{{ firstname }}">
                <input type="hidden" name="email" value="{{ email }}">
                <input type="hidden" name="phone" value="{{ phone }}">
                <input type="hidden" name="surl" value="{{ surl }}">
                <input type="hidden" name="furl" value="{{ furl }}">
                <input type="hidden" name="hash" value="{{ req_hash }}">
                <!-- Explicitly pass udf1..udf10 as empty -->
                {% for i in range(1, 11) %}
                <input type="hidden" name="udf{{ i }}" value="">
                {% endfor %}
                <noscript><button type="submit">Continue</button></noscript>
            </form>
        </body>
        </html>
        """,
            payu_url=payu_url,
            api_key=account.api_key,
            txnid=txnid,
            amount=amount_str,
            productinfo=productinfo,
            firstname=firstname,
            email=email,
            phone=phone,
            surl=url_for("student_fee.payu_callback", _external=True),
            furl=url_for("student_fee.payu_callback", _external=True),
            req_hash=req_hash,
        )

        return form_html

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Database error while initiating PayU payment")
        return "Database error while initiating payment.", 500
    except Exception:
        current_app.logger.exception("Unexpected error while initiating PayU payment")
        return "An error occurred while initiating payment.", 500


@student_fee_bp.route("/callback/payu", methods=["POST"])
def payu_callback():
    data = request.form.to_dict()
    try:
        txnid = data.get("txnid")
        if not txnid:
            current_app.logger.warning("PayU callback missing txnid")
            return "Missing transaction ID", 400

        payment = FeePayment.query.filter_by(order_id=txnid).first()
        if not payment:
            current_app.logger.warning(f"PayU callback: no payment for txnid={txnid}")
            return "Payment record not found", 404

        account = payment.account
        if not account:
            current_app.logger.error(
                f"PayU callback: payment {payment.id} has no linked account"
            )
            return "Account misconfigured", 500

        # Validate response hash (critical)
        if not _validate_payu_response(data, account.salt, account.api_key):
            current_app.logger.error(
                f"PayU callback hash validation failed for txnid={txnid}"
            )
            return "Invalid hash", 403

        # Avoid updating an already successful payment (idempotency)
        if payment.status == "Paid":
            current_app.logger.info(
                f"PayU callback: payment {payment.id} already paid, skipping update"
            )
            return "OK"

        # Map status
        status = (data.get("status") or "").lower()
        if status == "success":
            payment.status = "Paid"
        elif status in {"failure", "failed", "aborted", "dropped", "bounced"}:
            payment.status = "Failed"
        elif status == "pending":
            payment.status = "Pending"
        else:
            payment.status = "Unknown"

        payment.transaction_id = (
            data.get("mihpayid") or data.get("payuMoneyId") or payment.transaction_id
        )
        payment.payment_method = data.get("mode") or payment.payment_method
        payment.response = json.dumps(data, separators=(",", ":"))

        db.session.commit()
        current_app.logger.info(
            f"Payment {payment.id} ({txnid}) updated to {payment.status}"
        )

        return "OK"

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Database error during PayU callback")
        return "Database error", 500
    except Exception:
        current_app.logger.exception("Unexpected error during PayU callback")
        return "Internal server error", 500

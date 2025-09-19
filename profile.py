from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import User
from utils import save_uploaded_file, parse_string, parse_date, parse_decimal

profile_bp = Blueprint("profile_bp", __name__)


# ===========================
# Admin → Student List
# ===========================
@profile_bp.route("/profile/admin/students")
@login_required
def admin_students():
    if current_user.role != "Admin":
        flash("❌ Unauthorized access.", "danger")
        return redirect(url_for("dashboard"))

    students = User.query.filter_by(role="Student").order_by(User.id.asc()).all()
    return render_template("admin_students.html", students=students)


# ===========================
# Admin → Set Student Profile
# ===========================
@profile_bp.route("/profile/admin/set_student_profile/<int:student_id>", methods=["GET", "POST"])
@login_required
def set_student_profile(student_id):
    if current_user.role != "Admin":
        flash("❌ Unauthorized access.", "danger")
        return redirect(url_for("dashboard"))

    student = User.query.get_or_404(student_id)

    if request.method == "POST":
        # Personal Info
        student.name = parse_string(request.form.get("name"))
        student.enrollment_no = parse_string(request.form.get("enrollment_no"))
        student.scholar_no = parse_string(request.form.get("scholar_no"))
        student.roll_no = parse_string(request.form.get("roll_no"))
        student.section = parse_string(request.form.get("section"))
        student.program = parse_string(request.form.get("program"))
        student.branch = parse_string(request.form.get("branch"))
        student.year = parse_string(request.form.get("year"))
        student.semester = parse_string(request.form.get("semester")) # ✅ ADDED SEMESTER

        # Date of Birth
        student.dob = parse_date(request.form.get("dob"))
        student.admission_date = parse_date(request.form.get("admission_date"))

        # Contact & Identity
        student.gender = parse_string(request.form.get("gender"))
        student.blood_group = parse_string(request.form.get("blood_group"))
        student.nationality = parse_string(request.form.get("nationality"))
        student.religion = parse_string(request.form.get("religion"))
        student.marital_status = parse_string(request.form.get("marital_status"))
        student.aadhaar_no = parse_string(request.form.get("aadhaar_no"))
        student.contact = parse_string(request.form.get("mobile"))
        student.email = parse_string(request.form.get("email"))
        student.category = parse_string(request.form.get("category"))
        student.mother_tongue = parse_string(request.form.get("mother_tongue"))
        student.samagra_id = parse_string(request.form.get("samagra_id"))
        student.domicile_state = parse_string(request.form.get("domicile_state"))

        # Parent Info
        student.father_name = parse_string(request.form.get("father_name"))
        student.father_name_hindi = parse_string(request.form.get("father_name_hindi"))
        student.father_mobile = parse_string(request.form.get("father_mobile"))
        student.father_income = parse_decimal(request.form.get("father_income"))

        student.mother_name = parse_string(request.form.get("mother_name"))
        student.mother_name_hindi = parse_string(request.form.get("mother_name_hindi"))
        student.mother_mobile = parse_string(request.form.get("mother_mobile"))
        student.mother_income = parse_decimal(request.form.get("mother_income"))

        # Address
        student.permanent_address = parse_string(request.form.get("permanent_address"))
        student.permanent_city = parse_string(request.form.get("permanent_city"))
        student.permanent_state = parse_string(request.form.get("permanent_state"))
        student.permanent_pin = parse_string(request.form.get("permanent_pin"))

        student.local_address = parse_string(request.form.get("local_address"))
        student.local_city = parse_string(request.form.get("local_city"))
        student.local_state = parse_string(request.form.get("local_state"))
        student.local_pin = parse_string(request.form.get("local_pin"))

        # Bank Info
        student.bank_name = parse_string(request.form.get("bank_name"))
        student.bank_branch = parse_string(request.form.get("bank_branch"))
        student.bank_account_no = parse_string(request.form.get("bank_account_no"))
        student.bank_ifsc = parse_string(request.form.get("bank_ifsc"))

        # File Uploads
        owner = f"user{student.id}"
        for field in ["photo", "signature", "id_card", "certificate", "transcript"]:
            saved = save_uploaded_file(field, owner_prefix=owner)
            if saved:
                setattr(student, field, saved)

        # Save to DB
        db.session.commit()
        flash("✅ Student profile updated successfully!", "success")
        return redirect(url_for("profile_bp.set_student_profile", student_id=student.id))

    return render_template("admin_setprofile.html", student=student)


# ===========================
# Student → Profile View/Edit
# ===========================
@profile_bp.route("/profile/student-profile/<int:student_id>", methods=["GET", "POST"])
@login_required
def student_profile(student_id):
    student = User.query.get_or_404(student_id)

    if current_user.role != "Admin" and current_user.id != student.id:
        flash("❌ Unauthorized access.", "danger")
        return redirect(url_for("dashboard"))

    is_admin = current_user.role == "Admin"

    if request.method == "POST" and not is_admin:
        # Allow only photo upload for students (Year 1)
        if str(student.year) == "1" and not student.photo:
            saved = save_uploaded_file("photo", owner_prefix=f"user{student.id}")
            if saved:
                student.photo = saved
                db.session.commit()
                flash("✅ Profile photo uploaded!", "success")
        else:
            flash("❌ You cannot edit profile details.", "danger")

        return redirect(url_for("profile_bp.student_profile", student_id=student.id))

    return render_template("student_profile.html", student=student, is_admin=is_admin)
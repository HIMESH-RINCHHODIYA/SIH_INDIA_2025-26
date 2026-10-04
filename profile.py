import os

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from extensions import db
from models import User
from utils import parse_date, parse_decimal, parse_string, save_uploaded_file

profile_bp = Blueprint("profile_bp", __name__)


def _student_file_url(student, path):
    if not path:
        return None

    normalized_path = path.replace("\\", "/")
    if normalized_path.startswith("static/"):
        return url_for("static", filename=normalized_path.removeprefix("static/"))
    if normalized_path.startswith("uploads/"):
        return url_for(
            "profile_bp.legacy_student_upload",
            student_id=student.id,
            filename=os.path.basename(normalized_path),
        )
    return None


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
@profile_bp.route(
    "/profile/admin/set_student_profile/<int:student_id>", methods=["GET", "POST"]
)
@login_required
def set_student_profile(student_id):
    if current_user.role != "Admin":
        flash("❌ Unauthorized access.", "danger")
        return redirect(url_for("dashboard"))

    student = User.query.get_or_404(student_id)

    if request.method == "POST":
        string_fields = {
            "name": "name",
            "name_hindi": "name_hindi",
            "email": "email",
            "enrollment_no": "enrollment_no",
            "scholar_no": "scholar_no",
            "roll_no": "roll_no",
            "section": "section",
            "program": "program",
            "branch": "branch",
            "year": "year",
            "semester": "semester",
            "gender": "gender",
            "blood_group": "blood_group",
            "nationality": "nationality",
            "religion": "religion",
            "marital_status": "marital_status",
            "aadhaar_no": "aadhaar_no",
            "mobile": "contact",
            "category": "category",
            "mother_tongue": "mother_tongue",
            "samagra_id": "samagra_id",
            "domicile_state": "domicile_state",
            "father_name": "father_name",
            "father_name_hindi": "father_name_hindi",
            "father_mobile": "father_mobile",
            "father_occupation": "father_occupation",
            "mother_name": "mother_name",
            "mother_name_hindi": "mother_name_hindi",
            "mother_mobile": "mother_mobile",
            "mother_occupation": "mother_occupation",
            "permanent_address": "permanent_address",
            "permanent_city": "permanent_city",
            "permanent_state": "permanent_state",
            "permanent_pin": "permanent_pin",
            "local_address": "local_address",
            "local_city": "local_city",
            "local_state": "local_state",
            "local_pin": "local_pin",
            "bank_name": "bank_name",
            "bank_branch": "bank_branch",
            "bank_account_no": "bank_account_no",
            "bank_ifsc": "bank_ifsc",
        }
        for form_field, model_field in string_fields.items():
            if form_field in request.form:
                setattr(
                    student, model_field, parse_string(request.form.get(form_field))
                )

        if "dob" in request.form:
            student.dob = parse_date(request.form.get("dob"))
        if "admission_date" in request.form:
            student.admission_date = parse_date(request.form.get("admission_date"))
        if "father_income" in request.form:
            student.father_income = parse_decimal(request.form.get("father_income"))
        if "mother_income" in request.form:
            student.mother_income = parse_decimal(request.form.get("mother_income"))

        # File Uploads
        owner = f"user{student.id}"
        for field in ["photo", "signature", "id_card", "certificate", "transcript"]:
            saved = save_uploaded_file(
                field,
                owner_prefix=owner,
                folder=current_app.config["UPLOAD_FOLDER"],
            )
            if saved:
                stored_path = os.path.relpath(saved, current_app.root_path)
                setattr(student, field, stored_path.replace(os.sep, "/"))

        # Save to DB
        db.session.commit()
        flash("✅ Student profile updated successfully!", "success")
        return redirect(
            url_for("profile_bp.set_student_profile", student_id=student.id)
        )

    return render_template(
        "admin_setprofile.html",
        student=student,
        photo_url=_student_file_url(student, student.photo),
        signature_url=_student_file_url(student, student.signature),
    )


@profile_bp.route(
    "/profile/student/<int:student_id>/legacy-uploads/<path:filename>"
)
@login_required
def legacy_student_upload(student_id, filename):
    student = User.query.get_or_404(student_id)
    if current_user.role != "Admin" and current_user.id != student.id:
        abort(403)
    if (
        filename != os.path.basename(filename)
        or not filename.startswith(f"user{student.id}_")
    ):
        abort(404)

    return send_from_directory(
        os.path.join(current_app.root_path, "uploads"),
        filename,
    )


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
            saved = save_uploaded_file(
                "photo",
                owner_prefix=f"user{student.id}",
                folder=current_app.config["UPLOAD_FOLDER"],
            )
            if saved:
                stored_path = os.path.relpath(saved, current_app.root_path)
                student.photo = stored_path.replace(os.sep, "/")
                db.session.commit()
                flash("✅ Profile photo uploaded!", "success")
        else:
            flash("❌ You cannot edit profile details.", "danger")

        return redirect(url_for("profile_bp.student_profile", student_id=student.id))

    return render_template(
        "student_profile.html",
        student=student,
        is_admin=is_admin,
        photo_url=_student_file_url(student, student.photo),
        signature_url=_student_file_url(student, student.signature),
    )

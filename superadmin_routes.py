import os

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_login import login_required
from werkzeug.utils import secure_filename

from extensions import db
from models import College, SiteBranding
from utils import role_required, save_uploaded_file

# Blueprint
superadmin_bp = Blueprint("superadmin", __name__, url_prefix="/superadmin")
DEFAULT_LOGO_FORMATS = {
    ".png": ("image/png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    ".jpg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".gif": ("image/gif", lambda data: data.startswith((b"GIF87a", b"GIF89a"))),
    ".webp": (
        "image/webp",
        lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    ),
}


def _save_logo(owner_prefix):
    saved_path = save_uploaded_file(
        "logo",
        owner_prefix=owner_prefix,
        folder=current_app.config["UPLOAD_FOLDER"],
    )
    if not saved_path:
        return None
    return os.path.relpath(saved_path, current_app.static_folder).replace(os.sep, "/")


def _remove_logo(logo):
    if not logo:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(logo))
    if os.path.isfile(path):
        os.remove(path)


def _update_default_logo():
    branding = db.session.get(SiteBranding, 1)
    if branding is None:
        branding = SiteBranding(id=1)
        db.session.add(branding)

    if request.form.get("action") == "remove":
        branding.default_logo = None
        branding.default_logo_content_type = None
        db.session.commit()
        flash("The built-in default logo is now in use.", "success")
        return redirect(url_for("superadmin.colleges"))

    uploaded_file = request.files.get("default_logo")
    if uploaded_file is None or not uploaded_file.filename:
        flash("Choose an image to upload.", "warning")
        return redirect(url_for("superadmin.colleges"))

    extension = os.path.splitext(uploaded_file.filename)[1].lower()
    image_format = DEFAULT_LOGO_FORMATS.get(extension)
    image_data = uploaded_file.stream.read(5 * 1024 * 1024 + 1)
    if len(image_data) > 5 * 1024 * 1024:
        flash("The default logo must be 5 MB or smaller.", "danger")
        return redirect(url_for("superadmin.colleges"))
    if image_format is None or not image_format[1](image_data):
        flash("Upload a valid PNG, JPG, GIF, or WEBP image.", "danger")
        return redirect(url_for("superadmin.colleges"))

    branding.default_logo = image_data
    branding.default_logo_content_type = image_format[0]
    db.session.commit()
    flash("Default logo updated successfully.", "success")
    return redirect(url_for("superadmin.colleges"))


# ------------------ Manage Colleges ------------------ #
@superadmin_bp.route("/colleges", methods=["GET", "POST"])
@login_required
@role_required("SuperAdmin")
def colleges():
    """Add new college + list all colleges"""
    if request.method == "POST":
        if request.form.get("form_type") == "default_logo":
            return _update_default_logo()

        name = request.form.get("name", "").strip()
        domain = request.form.get("domain", "").strip().lower()

        if not name or not domain:
            flash("❌ Name and domain are required!", "danger")
            return redirect(url_for("superadmin.colleges"))

        exists = College.query.filter(
            db.or_(College.name == name, College.domain == domain)
        ).first()
        if exists:
            flash("⚠️ A college with this name or domain already exists.", "warning")
            return redirect(url_for("superadmin.colleges"))

        logo = _save_logo(f"college_{secure_filename(name)}")
        college = College(name=name, domain=domain, logo=logo)
        db.session.add(college)
        db.session.commit()
        flash("✅ College added successfully!", "success")
        return redirect(url_for("superadmin.colleges"))

    college_list = College.query.order_by(College.name).all()
    return render_template("superadmin_colleges.html", colleges=college_list)


# ------------------ Update College ------------------ #
@superadmin_bp.route("/colleges/update/<int:college_id>", methods=["GET", "POST"])
@login_required
@role_required("SuperAdmin")
def update_college(college_id):
    """Update college details"""
    college = College.query.get_or_404(college_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        domain = request.form.get("domain", "").strip().lower()
        if not name or not domain:
            flash("❌ Name and domain are required!", "danger")
            return redirect(url_for("superadmin.update_college", college_id=college.id))

        exists = College.query.filter(
            db.or_(College.name == name, College.domain == domain)
        ).filter(College.id != college.id).first()
        if exists:
            flash("⚠️ A college with this name or domain already exists.", "warning")
            return redirect(url_for("superadmin.update_college", college_id=college.id))

        college.name = name
        college.domain = domain
        old_logo = college.logo
        new_logo = _save_logo(f"college{college.id}")
        if new_logo:
            college.logo = new_logo

        db.session.commit()
        if new_logo and old_logo != new_logo:
            _remove_logo(old_logo)
        flash("✅ College updated successfully!", "success")
        return redirect(url_for("superadmin.colleges"))

    return render_template("superadmin_update_college.html", college=college)


@superadmin_bp.route("/colleges/delete/<int:college_id>", methods=["POST"])
@login_required
@role_required("SuperAdmin")
def delete_college(college_id):
    """Delete a college that has no dependent users or payments."""
    college = College.query.get_or_404(college_id)
    if college.users.count() or college.fee_payments.count():
        flash("This college still has users or fee payments and cannot be deleted.", "warning")
        return redirect(url_for("superadmin.colleges"))

    logo = college.logo
    db.session.delete(college)
    db.session.commit()
    _remove_logo(logo)
    flash("🗑️ College deleted successfully!", "info")
    return redirect(url_for("superadmin.colleges"))

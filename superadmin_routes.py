import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from extensions import db
from models import College
from utils import save_uploaded_file, role_required
from flask_login import login_required

# Blueprint
superadmin_bp = Blueprint("superadmin", __name__, url_prefix="/superadmin")

# ------------------ Manage Colleges ------------------ #
@superadmin_bp.route("/colleges", methods=["GET", "POST"])
@login_required
@role_required("SuperAdmin")
def colleges():
    """Add new college + list all colleges"""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        domain = request.form.get("domain", "").strip().lower()
        logo = save_uploaded_file("logo", owner_prefix="college", upload_folder=current_app.config["UPLOAD_FOLDER"])

        if not name or not domain:
            flash("❌ Name and domain are required!", "danger")
            return redirect(url_for("superadmin.colleges"))

        # Check duplicate domain
        if College.query.filter_by(domain=domain).first():
            flash("⚠️ A college with this domain already exists.", "warning")
            return redirect(url_for("superadmin.colleges"))

        college = College(name=name, domain=domain, logo=logo)
        db.session.add(college)
        db.session.commit()
        flash("✅ College added successfully!", "success")
        return redirect(url_for("superadmin.colleges"))

    colleges = College.query.order_by(College.name).all()
    return render_template("superadmin_colleges.html", colleges=colleges)


# ------------------ Update College ------------------ #
@superadmin_bp.route("/colleges/update/<int:college_id>", methods=["GET", "POST"])
@login_required
@role_required("SuperAdmin")
def update_college(college_id):
    """Update college details"""
    college = College.query.get_or_404(college_id)

    if request.method == "POST":
        college.name = request.form.get("name", college.name).strip()
        college.domain = request.form.get("domain", college.domain).strip().lower()

        new_logo = save_uploaded_file("logo", owner_prefix=f"college{college.id}", upload_folder=current_app.config["UPLOAD_FOLDER"])
        if new_logo:
            # ✅ Delete old logo file if exists
            if college.logo:
                old_logo_path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(college.logo))
                if os.path.exists(old_logo_path):
                    try:
                        os.remove(old_logo_path)
                    except Exception:
                        pass
            college.logo = new_logo

        db.session.commit()
        flash("✅ College updated successfully!", "success")
        return redirect(url_for("superadmin.colleges"))

    return render_template("superadmin_update_college.html", college=college)


# ------------------ Delete College ------------------ #
@superadmin_bp.route("/colleges/delete/<int:college_id>", methods=["POST"])
@login_required
@role_required("SuperAdmin")
def delete_college(college_id):
    """Delete a college"""
    college = College.query.get_or_404(college_id)

    # ✅ Remove logo file if exists
    if college.logo:
        logo_path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(college.logo))
        if os.path.exists(logo_path):
            try:
                os.remove(logo_path)
            except Exception:
                pass

    db.session.delete(college)
    db.session.commit()
    flash("🗑️ College deleted successfully!", "info")
    return redirect(url_for("superadmin.colleges"))

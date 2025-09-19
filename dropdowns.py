from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models import DropdownValue, Course

dropdowns_bp = Blueprint("dropdowns_bp", __name__)

# Supported dropdown fields
SUPPORTED_FIELDS = [
    "program", "branch", "year", "semester", "enroll", "scholar_no",
    "class", "section", "blood_group", "nationality", "religion",
    "category", "gender", "marital_status", "courses"
]

# -------------------- Admin UI -------------------- #
@dropdowns_bp.route("/manage")
@login_required
def manage_dropdowns():
    if current_user.role != "Admin":
        flash("⛔ Access Denied.", "danger")
        return redirect(url_for("dashboard"))
    return render_template("manage_dropdowns.html")

# -------------------- GET API -------------------- #
@dropdowns_bp.route("/dropdowns", methods=["GET"])
def get_dropdowns():
    """Return all dropdown values as JSON."""
    dropdown_data = {}
    for field in SUPPORTED_FIELDS:
        if field == "courses":
            courses = db.session.query(Course.course_name).distinct().all()
            dropdown_data["courses"] = [c[0] for c in courses if c[0]]
        else:
            values = (
                db.session.query(DropdownValue.value)
                .filter_by(field=field)
                .distinct()
                .all()
            )
            dropdown_data[field] = [v[0] for v in values]
    return jsonify(dropdown_data)

# -------------------- POST API -------------------- #
@dropdowns_bp.route("/dropdowns", methods=["POST"])
@login_required
def add_dropdown_value():
    """Admin can add dropdown values."""
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    field = data.get("field")
    value = data.get("value")

    if not field or not value:
        return jsonify({"error": "Field and value are required"}), 400

    if field not in SUPPORTED_FIELDS:
        return jsonify({"error": f"Invalid field"}), 400

    try:
        if field == "courses":
            exists = db.session.query(Course).filter_by(course_name=value).first()
            if exists:
                return jsonify({"message": f"Course '{value}' already exists."}), 200
            course_code = value[:6].upper()
            new_course = Course(course_name=value, course_code=course_code)
            db.session.add(new_course)
        else:
            exists = db.session.query(DropdownValue).filter_by(field=field, value=value).first()
            if exists:
                return jsonify({"message": f"Value '{value}' already exists in {field}."}), 200
            db.session.add(DropdownValue(field=field, value=value))

        db.session.commit()
        return jsonify({"message": f"Value '{value}' added to {field}."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# -------------------- DELETE API -------------------- #
@dropdowns_bp.route("/dropdowns", methods=["DELETE"])
@login_required
def delete_dropdown_value():
    """Admin can delete dropdown values."""
    if current_user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    field = data.get("field")
    value = data.get("value")

    if not field or not value:
        return jsonify({"error": "Field and value are required"}), 400

    try:
        if field == "courses":
            course = db.session.query(Course).filter_by(course_name=value).first()
            if not course:
                return jsonify({"error": f"Course '{value}' not found."}), 404
            db.session.delete(course)
        else:
            record = db.session.query(DropdownValue).filter_by(field=field, value=value).first()
            if not record:
                return jsonify({"error": f"Value '{value}' not found in {field}."}), 404
            db.session.delete(record)

        db.session.commit()
        return jsonify({"message": f"Value '{value}' deleted from {field}."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

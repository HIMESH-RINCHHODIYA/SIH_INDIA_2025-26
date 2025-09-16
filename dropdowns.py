from flask import Blueprint, jsonify
from extensions import db
from models import User

dropdown_bp = Blueprint("dropdowns", __name__)

@dropdown_bp.route("/api/dropdowns", methods=["GET"])
def get_dropdowns():
    programs = [p[0] for p in db.session.query(User.program).distinct().all()]
    branches = [b[0] for b in db.session.query(User.branch).distinct().all()]
    years = [y[0] for y in db.session.query(User.year).distinct().all()]
    sections = [s[0] for s in db.session.query(User.section).distinct().all()]

    dropdown_data = {
        "programs": programs,
        "branches": branches,
        "years": years,
        "sections": sections
    }

    return jsonify(dropdown_data)

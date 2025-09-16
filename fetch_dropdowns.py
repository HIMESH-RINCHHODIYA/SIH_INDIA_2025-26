from flask import Flask
from extensions import db
import os

# Import your models
from models import User, Attendance, FeePayment, FeeConfig

# Create Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    # Fetch distinct values
    programs = [p[0] for p in db.session.query(User.program).distinct().all()]
    branches = [b[0] for b in db.session.query(User.branch).distinct().all()]
    years = [y[0] for y in db.session.query(User.year).distinct().all()]
    sections = [s[0] for s in db.session.query(User.section).distinct().all()]

    # Combine into a dictionary for dropdowns
    dropdown_data = {
        "programs": programs,
        "branches": branches,
        "years": years,
        "sections": sections
    }

    print("Dropdown Data:")
    print(dropdown_data)

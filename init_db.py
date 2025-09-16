from flask import Flask
from extensions import db
import os

# Import your models so SQLAlchemy knows about them
from models import User, Attendance, FeePayment, FeeConfig

# Create Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize db with app
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    print("All tables created successfully!")

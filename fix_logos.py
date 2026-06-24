from app import app  # import your Flask app
from extensions import db
from models import College

with app.app_context():
    colleges = College.query.all()
    updated = 0

    for college in colleges:
        if college.logo and not college.logo.startswith("uploads/"):
            # prepend "uploads/" to old records
            college.logo = f"uploads/{college.logo}"
            updated += 1

    db.session.commit()
    print(f"✅ Fixed {updated} logo paths")

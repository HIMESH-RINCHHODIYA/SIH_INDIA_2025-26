from app import app, db

# Create tables
with app.app_context():
    db.create_all()
    print("All tables created successfully!")

import os
from app import app, db  # Make sure your app imports SQLAlchemy db

# ---------- Path to SQLite DB ----------
DB_PATH = os.path.join(app.instance_path, "sqlite3.db")

# ---------- Delete old DB ----------
if os.path.exists(DB_PATH):
    print(f"Removing old database: {DB_PATH}")
    os.remove(DB_PATH)
else:
    print(f"No existing database found at {DB_PATH}")

# ---------- Ensure instance folder exists ----------
os.makedirs(app.instance_path, exist_ok=True)

# ---------- Recreate all tables ----------
with app.app_context():
    print("Creating tables...")
    db.create_all()
    print("✅ All tables created successfully!")

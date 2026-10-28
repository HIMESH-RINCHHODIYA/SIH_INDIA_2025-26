import os

from app import app, db

with app.app_context():
    DB_PATH = db.engine.url.database
    db.engine.dispose()
    if os.path.exists(DB_PATH):
        print(f"Removing old database: {DB_PATH}")
        os.remove(DB_PATH)
    else:
        print(f"No existing database found at {DB_PATH}")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    print("Creating tables...")
    db.create_all()
    print("✅ All tables created successfully!")

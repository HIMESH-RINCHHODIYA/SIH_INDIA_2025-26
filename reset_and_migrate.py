import os
from alembic.config import Config
from alembic import command
from app import app

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

# ---------- Run Alembic migrations ----------
with app.app_context():
    alembic_cfg = Config("migrations/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{DB_PATH}")

    print("Running Alembic migrations...")
    command.upgrade(alembic_cfg, "head")
    print("✅ Database migrated successfully!")

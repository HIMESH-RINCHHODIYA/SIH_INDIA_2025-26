import os

from alembic import command
from alembic.config import Config

from app import app, db

# ---------- Recreate the current schema and align Alembic history ----------
with app.app_context():
    db_path = db.engine.url.database
    db.engine.dispose()
    if db_path and os.path.isfile(db_path):
        print(f"Removing old database: {db_path}")
        os.remove(db_path)
    elif db_path:
        print(f"No existing database found at {db_path}")

    if db_path:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print("Creating the current schema from registered models...")
    db.create_all()

    alembic_cfg = Config("migrations/alembic.ini")
    alembic_cfg.set_main_option(
        "sqlalchemy.url", db.engine.url.render_as_string(hide_password=False)
    )
    print("Stamping the database at the current Alembic head...")
    command.stamp(alembic_cfg, "head")
    print("✅ Database recreated and migration history aligned!")

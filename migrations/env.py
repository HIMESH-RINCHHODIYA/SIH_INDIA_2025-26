import logging
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic Config object
config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# Flask integration
try:
    from flask import current_app
    flask_app = current_app._get_current_object()
except RuntimeError:
    flask_app = None

# Get SQLAlchemy URL and metadata
if flask_app is not None:
    # Running inside Flask
    engine = flask_app.extensions["migrate"].db.get_engine()
    target_metadata = flask_app.extensions["migrate"].db.metadata
else:
    # Running standalone
    target_metadata = None
    engine = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

# ------------------------------
# 👇 New filter to control autogenerate
# ------------------------------
def include_object(object, name, type_, reflected, compare_to):
    """
    Decide which tables/indexes Alembic should include when checking for changes.
    """
    # Ignore noisy legacy/system tables in migrations
    if type_ == "table" and name in {
        "fee_payments",
        "hostel_allocations",
        "mess_menus",
        "rooms",
        "leave_requests",
        "hostel_fees",
        "maintenance_requests",
        "mess_attendance",
        "visitors",
    }:
        return False
    return True


def run_migrations_offline():
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object  # 👈 added here
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object  # 👈 added here
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
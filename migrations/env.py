import sys
import logging
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic Config object
config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# Flask integration
try:
    from flask import current_app
    flask_app = current_app._get_current_object()
except RuntimeError:
    flask_app = None

# Get SQLAlchemy URL and metadata
if flask_app is not None:
    # Running inside Flask
    engine = flask_app.extensions['migrate'].db.get_engine()
    target_metadata = flask_app.extensions['migrate'].db.metadata
else:
    # Running standalone
    target_metadata = None
    # engine_from_config reads sqlalchemy.url from alembic.ini
    engine = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

def run_migrations_offline():
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

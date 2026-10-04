"""Add Hindi names and parent occupations to student profiles.

Revision ID: c4a69d2f81e0
Revises: bd33084041be
Create Date: 2026-10-04 08:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "c4a69d2f81e0"
down_revision = "bd33084041be"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("name_hindi", sa.String(length=150)))
    op.add_column("users", sa.Column("father_occupation", sa.String(length=100)))
    op.add_column("users", sa.Column("mother_occupation", sa.String(length=100)))


def downgrade():
    op.drop_column("users", "mother_occupation")
    op.drop_column("users", "father_occupation")
    op.drop_column("users", "name_hindi")

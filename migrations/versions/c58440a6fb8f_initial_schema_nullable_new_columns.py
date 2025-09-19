"""Initial schema (create tables)

Revision ID: c58440a6fb8f
Revises: 
Create Date: 2025-09-16 13:12:15.566154
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c58440a6fb8f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ------------------ faculty_courses table ------------------
    op.create_table(
        'faculty_courses',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('faculty_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('course_id', sa.Integer, sa.ForeignKey('courses.id'), nullable=False),
        sa.Column('semester', sa.String(length=10), nullable=False),
        sa.Column('course_type', sa.String(length=20), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('program', sa.String(length=100), nullable=False),
        sa.Column('branch', sa.String(length=100), nullable=False),
        sa.Column('year', sa.String(length=10), nullable=False)
    )

    # ------------------ student_courses table ------------------
    op.create_table(
        'student_courses',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('student_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('course_id', sa.Integer, sa.ForeignKey('courses.id'), nullable=False),
        sa.Column('semester', sa.String(length=10), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(), nullable=True),
        sa.Column('program', sa.String(length=100), nullable=False),
        sa.Column('branch', sa.String(length=100), nullable=False),
        sa.Column('year', sa.String(length=10), nullable=False)
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('student_courses')
    op.drop_table('faculty_courses')

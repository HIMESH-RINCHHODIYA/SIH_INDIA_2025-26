from flask import Blueprint

faculty_stud_bp = Blueprint(
    'faculty_stud_bp', __name__,
    template_folder="templates"
)

from faculty_attendance import routes  # import routes after defining blueprint

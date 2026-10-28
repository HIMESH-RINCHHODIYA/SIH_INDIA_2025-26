from flask import Blueprint

faculty_stud_bp = Blueprint("faculty_stud_bp", __name__)

from . import routes

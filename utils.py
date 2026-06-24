import os, uuid, io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from assignment_models import Assignment, AssignmentSubmission
from flask import abort, request
from flask_login import current_user, login_manager
from werkzeug.utils import secure_filename
from sqlalchemy import func

# -----------------------------
# File Helpers
# -----------------------------
def unique_filename(original: str, prefix: str = "") -> str:
    base = secure_filename(original)
    name, ext = os.path.splitext(base)
    token = uuid.uuid4().hex
    return f"{prefix}_{token}_{name}{ext}" if prefix else f"{token}_{name}{ext}"

def save_uploaded_file(field_name, owner_prefix=None, folder="uploads"):
    file = request.files.get(field_name)
    if not file or file.filename == "":
        return None

    # sanitize and prefix filename
    filename = secure_filename(file.filename)
    if owner_prefix:
        filename = f"{owner_prefix}_{filename}"

    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    file.save(filepath)
    return filepath

# -----------------------------
# Role check
# -----------------------------
def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ===========================
# Parsing Helpers
# ===========================
def parse_decimal(value, default=None):
    if value is None: return default
    s = str(value).strip().replace(",", "")
    if s == "": return default
    try: return Decimal(s)
    except (InvalidOperation, ValueError): return default

def parse_string(value):
    if not value: return None
    s = str(value).strip()
    return s if s else None

def parse_date(value):
    if not value: return None
    formats = ["%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None

# -----------------------------
# Grade/GPA Helpers
# -----------------------------
def calculate_grade(marks, out_of=100):
    try:
        percent = (int(marks) / out_of) * 100
    except (TypeError, ZeroDivisionError):
        return "N/A", 0
    if percent >= 90: return "A+", 10
    elif percent >= 80: return "A", 9
    elif percent >= 70: return "B+", 8
    elif percent >= 60: return "B", 7
    elif percent >= 50: return "C", 6
    elif percent >= 40: return "D", 5
    else: return "F", 0

def calculate_sgpa(results):
    total_credits = sum(r.credits for r in results)
    if total_credits == 0: return 0.0
    return round(sum(r.credits * r.grade_point for r in results)/total_credits, 2)

def calculate_cgpa(all_results):
    total_credits = sum(r.credits for r in all_results)
    if total_credits == 0: return 0.0
    return round(sum(r.credits * r.grade_point for r in all_results)/total_credits, 2)

def calculate_percentage(results):
    total_marks = sum(r.marks for r in results)
    total_outof = sum(r.out_of for r in results)
    if total_outof == 0: return 0.0
    return round((total_marks/total_outof)*100, 2)

def calculate_percentile(student_id, semester, Result, db):
    scores = db.session.query(Result.student_id, func.sum(Result.marks))\
        .filter(Result.semester==semester, Result.approved_by_admin==True)\
        .group_by(Result.student_id).all()
    if not scores: return 0.0
    total = len(scores)
    student_total = next((s[1] for s in scores if s[0]==student_id), 0)
    rank = 1 + sum(1 for s in scores if s[1] > student_total)
    return round((1 - (rank-1)/total) * 100, 2)



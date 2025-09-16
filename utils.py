import os
import uuid
from functools import wraps
from werkzeug.utils import secure_filename
from flask import request, abort
from flask_login import current_user, login_manager
from decimal import Decimal, InvalidOperation
from datetime import datetime


# ===========================
# File Handling
# ===========================
def unique_filename(original: str, prefix: str = "") -> str:
    base = secure_filename(original)
    name, ext = os.path.splitext(base)
    token = uuid.uuid4().hex
    return f"{prefix}_{token}_{name}{ext}" if prefix else f"{token}_{name}{ext}"


def save_uploaded_file(field_name: str, owner_prefix: str = "", upload_folder="static/uploads"):
    """
    Save an uploaded file to static/uploads and return its relative path.
    If no file is uploaded, returns None.
    """
    file = request.files.get(field_name)
    if not file or file.filename == "":
        return None

    filename = unique_filename(file.filename, prefix=owner_prefix)
    filepath = os.path.join(upload_folder, filename)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)

    # ✅ Store relative path like "uploads/college_xxx.png"
    return os.path.join("uploads", filename)


# ===========================
# Auth / Role Handling
# ===========================
def role_required(*roles):
    """
    Restrict route access to specific roles.
    Usage: @role_required("Admin", "Faculty")
    """
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
# Form Helpers
# ===========================
def parse_decimal(value, default=None):
    """
    Safely parse a form string into Decimal or return default.
    - strips commas (e.g. "1,234.56")
    - returns default when value is None or empty string
    """
    if value is None:
        return default
    s = str(value).strip()
    if s == "":
        return default
    try:
        s = s.replace(",", "")
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return default


def parse_string(value):
    """Return stripped string or None for empty input."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s != "" else None


def parse_date(value):
    """
    Attempt to parse common date formats returned by forms.
    Returns a date object or None.
    """
    if not value:
        return None
    s = str(value).strip()
    if s == "":
        return None
    formats = ["%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

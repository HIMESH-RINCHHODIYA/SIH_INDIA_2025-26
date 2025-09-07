from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import os, random, uuid

# ------------------ Logging Setup ------------------ #
import logging
logging.basicConfig(
    filename="app.log",   # all errors will go here
    level=logging.ERROR,  # only log errors (not info/debug)
    format="%(asctime)s %(levelname)s %(message)s"
)

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ------------------ Paths & Folders ------------------ #
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------ App Config ------------------ #
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload cap (optional)

# ------------------ DB & Migrate ------------------ #
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ------------------ Login Manager ------------------ #
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"

# ------------------ User Model ------------------ #
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), default="Student")   # Student, Faculty, Admin, SuperAdmin
    verified = db.Column(db.Boolean, default=False)

    # Student Profile Fields
    dob = db.Column(db.String(20))
    contact = db.Column(db.String(20))
    program = db.Column(db.String(100))
    year = db.Column(db.String(10))
    branch = db.Column(db.String(100))
    roll_no = db.Column(db.String(50))
    admission_date = db.Column(db.String(20))
    photo = db.Column(db.String(200))      # File path
    id_card = db.Column(db.String(200))
    certificate = db.Column(db.String(200))
    transcript = db.Column(db.String(200))


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

# ------------------ Helpers ------------------ #
def unique_filename(original: str, prefix: str = "") -> str:
    """
    Make a filename unique to avoid overwrites:
    <prefix>_<uuid4>_<secure_base.ext>
    """
    base = secure_filename(original)
    name, ext = os.path.splitext(base)
    token = uuid.uuid4().hex
    if prefix:
        return f"{prefix}_{token}_{name}{ext}"
    return f"{token}_{name}{ext}"

def save_uploaded_file(field_name: str, owner_prefix: str = ""):
    """
    Save a file from request.files[field_name] if present; return relative path or None.
    """
    file = request.files.get(field_name)
    if not file or file.filename == "":
        return None
    filename = unique_filename(file.filename, prefix=owner_prefix)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    # Store as relative path so it works on any machine
    return os.path.join("static", "uploads", filename)

def role_required(*roles):
    """
    Simple decorator to restrict routes to specific roles.
    Usage: @role_required("Admin", "SuperAdmin")
    """
    def decorator(func):
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)  # Forbidden
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ------------------ Routes ------------------ #

@app.route("/")
def home():
    # Send authenticated users to the dashboard
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# ----------- Registration with OTP ----------- #
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "Student")

        if not email.endswith("@medicaps.ac.in"):
            flash("Only college domain emails are allowed!", "danger")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered!", "danger")
            return redirect(url_for("register"))

        new_user = User(
            name=name or email.split("@")[0],
            email=email,
            password=generate_password_hash(password, method="pbkdf2:sha256"),
            role=role,
            verified=False
        )
        db.session.add(new_user)
        db.session.commit()

        otp = str(random.randint(1000, 9999))
        session["otp"] = otp
        session["user_id"] = new_user.id
        flash(f"Your OTP (for demo): {otp}", "info")
        return redirect(url_for("verify_otp"))

    return render_template("register.html")

@app.route("/verify", methods=["GET", "POST"])
def verify_otp():
    # If already verified/logged in, go to dashboard
    if current_user.is_authenticated and current_user.verified:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        entered_otp = request.form.get("otp")
        if entered_otp == session.get("otp"):
            uid = session.get("user_id")
            user = User.query.get(uid)
            if user:
                user.verified = True
                db.session.commit()
            # Clean up session values safely
            session.pop("otp", None)
            session.pop("user_id", None)
            flash("Email verified successfully! Please log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid OTP!", "danger")
    return render_template("verify.html")

# ----------- Login ----------- #
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash("Invalid credentials!", "danger")
            return redirect(url_for("login"))

        if not user.verified:
            # store for convenience in verification flow
            session["user_id"] = user.id
            flash("Please verify your email before logging in.", "warning")
            return redirect(url_for("verify_otp"))

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")

# ----------- Dashboard ----------- #
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", name=current_user.name, role=current_user.role)

# ----------- Profile Management ----------- #
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.dob = request.form.get("dob")
        current_user.contact = request.form.get("contact")
        current_user.program = request.form.get("program")
        current_user.year = request.form.get("year")
        current_user.branch = request.form.get("branch")
        current_user.roll_no = request.form.get("roll_no")
        current_user.admission_date = request.form.get("admission_date")

        # File uploads (unique names per user)
        owner = f"user{current_user.id}"
        for field in ["photo", "id_card", "certificate", "transcript"]:
            saved = save_uploaded_file(field, owner_prefix=owner)
            if saved:
                setattr(current_user, field, saved)

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=current_user)

# ----------- Forgot & Reset Password ----------- #
@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account with this email!", "danger")
            return redirect(url_for("forgot_password"))

        otp = str(random.randint(1000, 9999))
        session["reset_otp"] = otp
        session["reset_user"] = user.id
        flash(f"Password reset OTP (for demo): {otp}", "info")
        return redirect(url_for("reset_password"))

    return render_template("forgot.html")

@app.route("/reset", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        otp = request.form.get("otp")
        new_password = request.form.get("password", "")

        if otp == session.get("reset_otp"):
            user = User.query.get(session.get("reset_user"))
            if user:
                user.password = generate_password_hash(new_password, method="pbkdf2:sha256")
                db.session.commit()
            session.pop("reset_otp", None)
            session.pop("reset_user", None)
            flash("Password reset successful! Please login.", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid OTP!", "danger")

    return render_template("reset.html")

# ----------- Logout ----------- #
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# ----------- Student Profile ----------- #
@app.route("/student-profile", methods=["GET", "POST"])
@login_required
def student_profile():
    if request.method == "POST":
        # Personal details
        current_user.name = request.form.get("name") or current_user.name
        current_user.dob = request.form.get("dob")
        current_user.contact = request.form.get("contact")

        # Academic details
        current_user.program = request.form.get("program")
        current_user.year = request.form.get("year")
        current_user.branch = request.form.get("branch")
        current_user.roll_no = request.form.get("roll_no")
        current_user.admission_date = request.form.get("admission_date")

        # Document uploads
        owner = f"user{current_user.id}"
        for field in ["photo", "id_card", "certificate", "transcript"]:
            saved = save_uploaded_file(field, owner_prefix=owner)
            if saved:
                setattr(current_user, field, saved)

        db.session.commit()
        flash("Profile details saved successfully!", "success")
        return redirect(url_for("student_profile"))

    return render_template("student_profile.html", user=current_user)

# ================== NEW FEATURES FROM THE IMAGE ================== #

# ================== COMING SOON FEATURES ================== #

# ----------- Jobs ----------- #
@app.route("/jobs")
@login_required
def jobs():
    return render_template("coming_soon.html")

# ----------- Webinars ----------- #
@app.route("/webinars")
@login_required
def webinars():
    return render_template("coming_soon.html")

# ----------- Forums ----------- #
@app.route("/forums")
@login_required
def forums():
    return render_template("coming_soon.html")

# ----------- People ----------- #
@app.route("/people")
@login_required
def people():
    return render_template("coming_soon.html")

# ----------- Assessments ----------- #
@app.route("/assessments")
@login_required
def assessments():
    return render_template("coming_soon.html")

# ----------- Practice Tests ----------- #
@app.route("/practice-tests")
@login_required
def practice_tests():
    return render_template("coming_soon.html")

# ----------- Assignments ----------- #
@app.route("/assignments")
@login_required
def assignments():
    return render_template("coming_soon.html")

# ----------- Resumes ----------- #
@app.route("/resumes")
@login_required
def resumes():
    return render_template("coming_soon.html")

# ----------- Academics ----------- #
@app.route("/academics")
@login_required
def academics():
    return render_template("coming_soon.html")

# ----------- Cohorts ----------- #
@app.route("/cohorts")
@login_required
def cohorts():
    return render_template("coming_soon.html")

# ----------- My Program ----------- #
@app.route("/my-program")
@login_required
def my_program():
    return render_template("coming_soon.html")

# ================== EXISTING DASHBOARD ROUTES ================== #

# ----------- Student ----------- #
@app.route("/student/attendance")
@login_required
def student_attendance():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="📚 Student Attendance",
                           content="Here you can view your attendance records.")

@app.route("/student/grades")
@login_required
def student_grades():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="📊 Student Grades",
                           content="Here you can check your academic grades.")

@app.route("/student/fees")
@login_required
def student_fees():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="💰 Student Fees",
                           content="Here you can check and pay your fees.")

# ----------- Faculty ----------- #
@app.route("/faculty/courses")
@login_required
@role_required("Faculty", "Admin", "SuperAdmin")
def faculty_courses():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="📖 Faculty Courses",
                           content="Manage your courses here.")

@app.route("/faculty/assignments")
@login_required
@role_required("Faculty", "Admin", "SuperAdmin")
def faculty_assignments():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="📝 Faculty Assignments",
                           content="Upload and manage assignments.")

@app.route("/faculty/attendance")
@login_required
@role_required("Faculty", "Admin", "SuperAdmin")
def faculty_attendance():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="✅ Faculty Attendance",
                           content="Mark and manage student attendance.")

# ----------- Admin ----------- #
@app.route("/admin/admissions")
@login_required
@role_required("Admin", "SuperAdmin")
def admin_admissions():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="🛠️ Admin Admissions",
                           content="Approve or reject student admissions.")

@app.route("/admin/reports")
@login_required
@role_required("Admin", "SuperAdmin")
def admin_reports():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="📑 Admin Reports",
                           content="Generate and view reports.")

@app.route("/admin/users")
@login_required
@role_required("Admin", "SuperAdmin")
def admin_users():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="👥 Admin Users",
                           content="Manage user accounts and roles.")

# ----------- SuperAdmin ----------- #
@app.route("/superadmin/manage")
@login_required
@role_required("SuperAdmin")
def superadmin_manage():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="🌍 Super Admin - ERP Management",
                           content="Manage the entire ERP system.")

@app.route("/superadmin/roles")
@login_required
@role_required("SuperAdmin")
def superadmin_roles():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="🔑 Super Admin - Roles",
                           content="Manage user roles and permissions.")

@app.route("/superadmin/logs")
@login_required
@role_required("SuperAdmin")
def superadmin_logs():
    return render_template("dashboard_page.html",
                           user=current_user,
                           title="📂 Super Admin - System Logs",
                           content="View system logs and activities.")
    
    # ------------------ Error Handlers ------------------ #
@app.errorhandler(403)
def forbidden_error(error):
    logging.error(f"403 Forbidden: {error}")
    return render_template("coming_soon.html", message="Access Forbidden (403)"), 403

@app.errorhandler(404)
def not_found_error(error):
    logging.error(f"404 Not Found: {error}")
    return render_template("coming_soon.html", message="Page Not Found (404)"), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"500 Internal Server Error: {error}")
    return render_template("coming_soon.html", message="Server Error (500)"), 500


# ------------------ Run App ------------------ #
if __name__ == "__main__":
    # Optional: create tables if running without migrations in dev
    with app.app_context():
        db.create_all()
    app.run(debug=True)
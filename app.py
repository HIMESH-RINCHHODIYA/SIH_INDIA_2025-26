# app.py
import os
import random
import socket
import tempfile

from dotenv import load_dotenv
from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, session, url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
# Import models so they are registered with SQLAlchemy
from hostel_models import (Hostel, HostelAllocation, HostelComplaint,
                           HostelLeave, HostelRoom)
from library_models import Book, BorrowRecord, Penalty
from models import College, SiteBranding, User
from utils import role_required

load_dotenv()

# ------------------ App Setup ------------------ #
app = Flask(__name__, template_folder="templates")

# ------------------ Paths & Folders ------------------ #
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
is_vercel = os.getenv("VERCEL") == "1"
database_url = os.getenv("DATABASE_URL")
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql+psycopg://", 1
        )
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )
if is_vercel and (not database_url or database_url.startswith("sqlite:")):
    # Vercel's deployment filesystem is read-only; /tmp is writable but ephemeral.
    database_path = os.path.join(tempfile.gettempdir(), "sih_india_erp.sqlite3")
    database_url = f"sqlite:///{database_path}"
elif not database_url:
    database_url = "sqlite:///db.sqlite3"
if not is_vercel:
    os.makedirs(app.instance_path, exist_ok=True)

# ------------------ App Config ------------------ #
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "supersecretkey")
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# Allowed extensions for uploads
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "svg"}

# ------------------ Initialize Extensions ------------------ #
db.init_app(app)
migrate = Migrate(app, db)

# ------------------ Flask-Login ------------------ #
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ------------------ Ensure DB Tables Exist ------------------ #
with app.app_context():
    db.create_all()
    print("✅ All tables created or already exist")
    print("✅ All database tables ensured!")

from profile import profile_bp

from admin_fee import admin_fee_bp
from blueprints.library_bp import library_bp
from blueprints.library_chatbot_bp import chatbot_bp
from course_routes import course_bp
from dropdowns import dropdowns_bp
from faculty_attendance import faculty_stud_bp
from grades_bp import grades_bp
from hostel import hostel_bp
# Import your blueprints
from student_att import student_bp
from student_fee import student_fee_bp
from superadmin_routes import superadmin_bp
from assignment_ import assignment_bp

# Register Blueprints
app.register_blueprint(student_bp, url_prefix="/student")
app.register_blueprint(faculty_stud_bp, url_prefix="/faculty")
app.register_blueprint(student_fee_bp)
app.register_blueprint(admin_fee_bp)
app.register_blueprint(dropdowns_bp, url_prefix="/api")
app.register_blueprint(grades_bp, url_prefix="/grades")
app.register_blueprint(superadmin_bp, url_prefix="/superadmin")
app.register_blueprint(course_bp, url_prefix="/courses")
app.register_blueprint(profile_bp, url_prefix="/profile")
app.register_blueprint(hostel_bp)
app.register_blueprint(library_bp)
app.register_blueprint(chatbot_bp)
app.register_blueprint(assignment_bp)


@app.route("/default-logo")
def default_logo():
    branding = db.session.get(SiteBranding, 1)
    if branding and branding.default_logo:
        response = Response(
            branding.default_logo,
            mimetype=branding.default_logo_content_type or "image/png",
        )
    else:
        response = Response(
            """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
              <rect width="64" height="64" rx="12" fill="#f8f9fa"/>
              <path d="M8 24 32 10l24 14-24 14z" fill="#0d6efd"/>
              <path d="M16 31v16h32V31L32 40z" fill="#212529"/>
              <path d="M25 37h14v10H25z" fill="#f8f9fa"/>
              <path d="M5 53h54v4H5z" fill="#0d6efd"/>
            </svg>""",
            mimetype="image/svg+xml",
        )
    response.headers["Cache-Control"] = "no-store"
    return response


# ------------------ Routes ------------------ #
@app.route("/")
def home():
    return redirect(
        url_for("dashboard") if current_user.is_authenticated else url_for("login")
    )


@app.route("/dashboard")
@login_required
def dashboard():
    """
    Pass college_logo (if any) so templates can display:
    In template: <img src="{{ url_for('static', filename=college_logo) }}"> when college_logo is not None
    """
    college_logo = None
    if current_user.college_id:
        college = College.query.get(current_user.college_id)
        if college and college.logo:
            # college.logo stored as "uploads/filename.ext"
            college_logo = college.logo
    # Optionally, SuperAdmin might want a global logo or none.
    return render_template(
        "dashboard.html",
        name=current_user.name,
        role=current_user.role,
        college_logo=college_logo,
    )


# ------------------ Registration & OTP ------------------ #
@app.route("/register", methods=["GET", "POST"])
def register():
    colleges = College.query.order_by(College.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "Student")
        college_id = request.form.get("college_id")

        college = None
        if role != "SuperAdmin":
            # For Students/Admins, a college must be selected
            college = College.query.get(int(college_id)) if college_id else None
            if not college:
                flash("Please select a valid college.", "danger")
                return redirect(url_for("register"))

            # Validate email domain matches selected college
            allowed_domain = college.domain.lower()
            if not email.endswith(f"@{allowed_domain}"):
                flash(f"Email must end with @{allowed_domain}", "danger")
                return redirect(url_for("register"))

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
            return redirect(url_for("register"))

        # Create user
        user = User(
            name=name or email.split("@")[0],
            email=email,
            password=generate_password_hash(password, method="pbkdf2:sha256"),
            role=role,
            college_id=college.id if college else None,
            verified=False,
        )
        db.session.add(user)
        db.session.commit()

        otp = str(random.randint(1000, 9999))
        session["otp"] = otp
        session["user_id"] = user.id
        flash(f"OTP for demo: {otp}", "info")
        return redirect(url_for("verify_otp"))

    return render_template("register.html", colleges=colleges)


@app.route("/verify", methods=["GET", "POST"])
def verify_otp():
    if current_user.is_authenticated and current_user.verified:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        entered = request.form.get("otp")
        if entered == session.get("otp"):
            user = User.query.get(session.get("user_id"))
            if user:
                user.verified = True
                db.session.commit()
            session.pop("otp", None)
            session.pop("user_id", None)
            flash("Email verified successfully!", "success")
            return redirect(url_for("login"))
        flash("Invalid OTP!", "danger")
    return render_template("verify.html")


# ----------- Login -----------
# ----------- Login -----------
@app.route("/login", methods=["GET", "POST"])
def login():
    colleges = College.query.order_by(College.name).all()

    if request.method == "POST":
        college_id = request.form.get("college_id")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # get user by email only
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid credentials!", "danger")
            return redirect(url_for("login"))

        # If not superadmin, require college selection and validate
        if user.role != "SuperAdmin":
            if not college_id:
                flash("Please select a college!", "danger")
                return redirect(url_for("login"))
            if str(user.college_id) != str(college_id):
                flash("Invalid college selected!", "danger")
                return redirect(url_for("login"))

            # ✅ Fetch the correct college
            college = College.query.get(int(college_id))
        else:
            college = None

        if not user.verified:
            session["user_id"] = user.id
            flash("Verify your email first.", "warning")
            return redirect(url_for("verify_otp"))

        login_user(user)

        # ✅ Store correct college info in session
        if user.role == "SuperAdmin":
            session["college_logo"] = None
            session["college_name"] = "College ERP"
        else:
            # ✅ Always use the college assigned to the user in DB
            college = College.query.get(user.college_id)
        if college:
            session["college_logo"] = college.logo
            session["college_name"] = college.name
        else:
            session["college_logo"] = None
            session["college_name"] = "College ERP"

        return redirect(url_for("dashboard"))

    return render_template("login.html", colleges=colleges)


# ----------- Logout ----------- #
@app.route("/logout")
def logout():
    logout_user()

    # ✅ Clear college-specific session data
    session.pop("college_logo", None)
    session.pop("college_name", None)

    flash("Logged out.", "info")
    return redirect(url_for("login"))


# ----------- Profile ----------- #
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if current_user.role == "Student":
        return redirect(
            url_for("profile_bp.student_profile", student_id=current_user.id)
        )
    if current_user.role == "Admin":
        return redirect(url_for("profile_bp.admin_students"))
    return redirect(url_for("dashboard"))


# ----------- Forgot / Reset ----------- #
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
        flash(f"Reset OTP for demo: {otp}", "info")
        return redirect(url_for("reset_password"))
    return render_template("forgot.html")


@app.route("/reset", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        otp = request.form.get("otp")
        pwd = request.form.get("password", "")
        if otp == session.get("reset_otp"):
            user = User.query.get(session.get("reset_user"))
            if user:
                user.password = generate_password_hash(pwd, method="pbkdf2:sha256")
                db.session.commit()
            session.pop("reset_otp", None)
            session.pop("reset_user", None)
            flash("Password reset successfully!", "success")
            return redirect(url_for("login"))
        flash("Invalid OTP!", "danger")
    return render_template("reset.html")


# ------------------ Coming Soon Features ------------------ #
@app.route("/jobs")
@app.route("/webinars")
@app.route("/forums")
@app.route("/people")
@app.route("/assessments")
@app.route("/practice-tests")
@app.route("/assignments")
@app.route("/resumes")
@app.route("/academics")
@app.route("/cohorts")
@app.route("/my-program")
@login_required
def coming_soon():
    return render_template("coming_soon.html")


# ------------------ Student Dashboard Pages ------------------ #
@app.route("/student/<string:path>")
@login_required
def student_pages(path):
    # ✅ Ensure role check is case-insensitive
    if current_user.role.lower() != "student":
        return redirect(url_for("dashboard"))

    # ✅ Allowed pages
    title_map = {"grades": "📊 Student Grades", "fees": "💰 Student Fees"}
    content_map = {"grades": "Check academic grades", "fees": "Check/pay fees"}

    # ❌ Invalid page -> 404
    if path not in title_map:
        abort(404)

    # ✅ Render student dashboard page
    return render_template(
        "dashboard_page.html",
        user=current_user,
        title=title_map[path],
        content=content_map[path],
    )


# ------------------ Faculty Dashboard Pages ------------------ #
@app.route("/faculty/<path>")
@login_required
@role_required("Faculty", "Admin", "SuperAdmin")
def faculty_pages(path):
    title_map = {
        "courses": "📖 Faculty Courses",
        "assignments": "📝 Faculty Assignments",
        "attendance": "🗓 Faculty Attendance",
    }
    content_map = {
        "courses": "Manage courses",
        "assignments": "Upload/manage assignments",
        "attendance": "Mark and manage student attendance",
    }

    if path not in title_map:
        abort(404)

    return render_template(
        "dashboard_page.html",
        user=current_user,
        title=title_map[path],
        content=content_map[path],
    )


# ------------------ Error Handlers ------------------ #
@app.errorhandler(403)
def forbidden(error):
    return render_template("coming_soon.html", message="403 Forbidden"), 403


@app.errorhandler(404)
def not_found(error):
    return render_template("coming_soon.html", message="404 Not Found"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("coming_soon.html", message="500 Server Error"), 500


# ------------------ Run App ------------------ #
def find_free_port(default=5000):
    port = default
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1


if __name__ == "__main__":
    free_port = find_free_port(5000)
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", free_port))
    print(f"Starting Flask on {host}:{port}")
    app.run(debug=True, host=host, port=port, use_reloader=False)

# app.py
import os
import random
import uuid
import datetime
import socket
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from functools import wraps

from extensions import db
from models import User, Attendance, FeePayment, FeeConfig, College
from utils import save_uploaded_file, role_required
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

# ------------------ App Setup ------------------ #
app = Flask(__name__, template_folder="templates")

# ------------------ Paths & Folders ------------------ #
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------ App Config ------------------ #
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///db.sqlite3'  # main database
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

# ------------------ Blueprints ------------------ #
from student_att import student_bp
from faculty_attendance import faculty_stud_bp
from student_fee import student_fee_bp
from admin_fee import admin_fee
from dropdowns import dropdowns_bp
from grades_bp import grades_bp
from superadmin_routes import superadmin_bp
from course_routes import course_bp
from profile import profile_bp

# ------------------ Register Blueprints ------------------ #
app.register_blueprint(student_bp, url_prefix="/student")
app.register_blueprint(faculty_stud_bp, url_prefix="/faculty")
app.register_blueprint(student_fee_bp, url_prefix="/student")
app.register_blueprint(admin_fee, url_prefix="/admin")
app.register_blueprint(dropdowns_bp, url_prefix="/api")
app.register_blueprint(grades_bp, url_prefix="/grades")
app.register_blueprint(superadmin_bp, url_prefix="/superadmin")
app.register_blueprint(course_bp, url_prefix="/courses")
app.register_blueprint(profile_bp, url_prefix="/profile")

# ------------------ Routes ------------------ #
@app.route("/")
def home():
    return redirect(url_for("dashboard") if current_user.is_authenticated else url_for("login"))

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
    return render_template("dashboard.html", name=current_user.name, role=current_user.role, college_logo=college_logo)

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
            verified=False
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
    if request.method == "POST":
        for field in ["dob","contact","program","year","branch","roll_no","admission_date"]:
            setattr(current_user, field, request.form.get(field))
        owner = f"user{current_user.id}"
        for field in ["photo","id_card","certificate","transcript"]:
            saved = save_uploaded_file(field, owner_prefix=owner)
            if saved: setattr(current_user, field, saved)
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=current_user)

# ----------- Forgot / Reset ----------- #
@app.route("/forgot", methods=["GET","POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account with this email!", "danger")
            return redirect(url_for("forgot_password"))
        otp = str(random.randint(1000,9999))
        session["reset_otp"] = otp
        session["reset_user"] = user.id
        flash(f"Reset OTP for demo: {otp}","info")
        return redirect(url_for("reset_password"))
    return render_template("forgot.html")

@app.route("/reset", methods=["GET","POST"])
def reset_password():
    if request.method=="POST":
        otp=request.form.get("otp")
        pwd=request.form.get("password","")
        if otp==session.get("reset_otp"):
            user=User.query.get(session.get("reset_user"))
            if user:
                user.password=generate_password_hash(pwd, method="pbkdf2:sha256")
                db.session.commit()
            session.pop("reset_otp",None)
            session.pop("reset_user",None)
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
    title_map = {
        "grades": "📊 Student Grades",
        "fees": "💰 Student Fees"
    }
    content_map = {
        "grades": "Check academic grades",
        "fees": "Check/pay fees"
    }

    # ❌ Invalid page -> 404
    if path not in title_map:
        abort(404)

    # ✅ Render student dashboard page
    return render_template(
        "dashboard_page.html",
        user=current_user,
        title=title_map[path],
        content=content_map[path]
    )

# ------------------ Faculty Dashboard Pages ------------------ #
@app.route("/faculty/<path>")
@login_required
@role_required("Faculty","Admin","SuperAdmin")
def faculty_pages(path):
    title_map = {
        "courses": "📖 Faculty Courses",
        "assignments": "📝 Faculty Assignments",
        "attendance": "🗓 Faculty Attendance"
    }
    content_map = {
        "courses": "Manage courses",
        "assignments": "Upload/manage assignments",
        "attendance": "Mark and manage student attendance"
    }

    if path not in title_map:
        abort(404)

    return render_template(
        "dashboard_page.html",
        user=current_user,
        title=title_map[path],
        content=content_map[path]
    )

# ------------------ Faculty Attendance (core feature) ------------------ #
@app.route("/faculty/attendance", methods=["GET","POST"])
@login_required
@role_required("Faculty","Admin","SuperAdmin")
def faculty_attendance():
    students = []
    selected_class = request.args.get("class") or request.args.get("class_")  # support both query keys
    selected_branch = request.args.get("branch")
    selected_date = request.args.get("date", datetime.datetime.today().strftime("%Y-%m-%d"))

    # Build lists for dropdowns
    classes_query = db.session.query(User.year).filter_by(role="Student").distinct().all()
    classes = [c[0] for c in classes_query if c[0]]
    branches_query = db.session.query(User.branch).filter_by(role="Student").distinct().all()
    branches = [b[0] for b in branches_query if b[0]]

    if request.method == "POST":
        selected_class = request.form.get("class")
        selected_branch = request.form.get("branch")
        selected_date = request.form.get("date")
        try:
            selected_date_obj = datetime.datetime.strptime(selected_date, "%Y-%m-%d").date()
        except Exception:
            flash("Invalid date!", "danger")
            return redirect(url_for("faculty_attendance"))

        # fetch students for the chosen class+branch
        students = User.query.filter_by(role="Student", year=selected_class, branch=selected_branch).order_by(User.roll_no).all()

        # remove existing attendance rows for same date/class/branch (for those students) to avoid duplicates
        student_ids = [s.id for s in students]
        if student_ids:
            db.session.query(Attendance).filter(
                Attendance.student_id.in_(student_ids),
                Attendance.date == selected_date_obj,
                Attendance.branch == selected_branch,
                Attendance.class_name == selected_class
            ).delete(synchronize_session=False)

        # create records from submitted form
        for s in students:
            present = request.form.get(f"attendance_{s.id}") == "on"
            rec = Attendance(
                student_id=s.id,
                date=selected_date_obj,
                branch=selected_branch,
                class_name=selected_class,
                status="Present" if present else "Absent"
            )
            db.session.add(rec)

        db.session.commit()
        flash("Attendance saved!", "success")
        # redirect with query params to show the selected list
        return redirect(url_for("faculty_attendance", branch=selected_branch, class_=selected_class, date=selected_date))

    # if it's a GET with query params, show students for the selected class/branch
    if selected_class and selected_branch:
        students = User.query.filter_by(role="Student", year=selected_class, branch=selected_branch).order_by(User.roll_no).all()

    # fetch existing attendance for display (if any)
    existing_attendance = []
    try:
        date_obj = datetime.datetime.strptime(selected_date, "%Y-%m-%d").date()
        if students:
            existing_attendance = Attendance.query.filter(
                Attendance.student_id.in_([s.id for s in students]),
                Attendance.date == date_obj,
                Attendance.branch == selected_branch,
                Attendance.class_name == selected_class
            ).all()
    except Exception:
        existing_attendance = []

    # build a quick lookup for status per student
    attendance_map = {a.student_id: a.status for a in existing_attendance}

    return render_template(
        "faculty_stud.html",
        user=current_user,
        classes=classes,
        branches=branches,
        students=students,
        selected_class=selected_class,
        selected_branch=selected_branch,
        selected_date=selected_date,
        attendance_map=attendance_map
    )

# ------------------ SuperAdmin: College Management (CRUD) ------------------ #
@app.route("/superadmin/colleges", methods=["GET", "POST"])
@login_required
@role_required("SuperAdmin")
def superadmin_colleges():
    """
    List all colleges and allow creation via POST.
    POST params: name, domain, logo (file)
    """
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        domain = request.form.get("domain", "").strip().lower()
        if not name or not domain:
            flash("Name and domain are required.", "danger")
            return redirect(url_for("superadmin_colleges"))

        if College.query.filter(db.or_(College.name == name, College.domain == domain)).first():
            flash("College with same name or domain exists.", "danger")
            return redirect(url_for("superadmin_colleges"))

        # handle logo upload
        logo_saved = save_uploaded_file("logo", owner_prefix=f"college_{secure_filename(name)}")
        logo_db_path = None
        if logo_saved:
            # stored as "uploads/filename" — map to "uploads/filename" for DB and url_for('static', filename=...)
            logo_db_path = logo_saved

        new_college = College(name=name, domain=domain, logo=logo_db_path)
        db.session.add(new_college)
        db.session.commit()
        flash("College added successfully.", "success")
        return redirect(url_for("superadmin_colleges"))

    colleges = College.query.order_by(College.name).all()
    return render_template("superadmin/manage_colleges.html", colleges=colleges)

@app.route("/superadmin/colleges/<int:college_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("SuperAdmin")
def edit_college(college_id):
    college = College.query.get_or_404(college_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        domain = request.form.get("domain", "").strip().lower()
        remove_logo = request.form.get("remove_logo") == "on"

        if not name or not domain:
            flash("Name and domain are required.", "danger")
            return redirect(url_for("edit_college", college_id=college_id))

        # check uniqueness excluding current
        exists = College.query.filter(db.or_(College.name == name, College.domain == domain)).filter(College.id != college.id).first()
        if exists:
            flash("Another college with same name or domain exists.", "danger")
            return redirect(url_for("edit_college", college_id=college_id))

        college.name = name
        college.domain = domain

        # handle logo file
        logo_saved = save_uploaded_file("logo", owner_prefix=f"college_{secure_filename(name)}")
        if logo_saved:
            college.logo = logo_saved
        elif remove_logo:
            college.logo = None

        db.session.commit()
        flash("College updated successfully.", "success")
        return redirect(url_for("superadmin_colleges"))
    return render_template("superadmin/edit_college.html", college=college)

@app.route("/superadmin/colleges/<int:college_id>/delete", methods=["POST"])
@login_required
@role_required("SuperAdmin")
def delete_college(college_id):
    college = College.query.get_or_404(college_id)
    # Optional: unlink logo file from disk if you want to remove physical file
    if college.logo:
        try:
            logo_full_path = os.path.join(app.static_folder, college.logo)  # static/uploads/...
            if os.path.exists(logo_full_path):
                os.remove(logo_full_path)
        except Exception:
            # fail silently for file deletion; DB deletion will still proceed
            pass
    # If there are dependent users, you might want to reassign or block deletion — currently this will attempt to delete
    db.session.delete(college)
    db.session.commit()
    flash("College deleted.", "info")
    return redirect(url_for("superadmin_colleges"))

# ------------------ Error Handlers ------------------ #
@app.errorhandler(403)
def forbidden(error): return render_template("coming_soon.html", message="403 Forbidden"),403
@app.errorhandler(404)
def not_found(error): return render_template("coming_soon.html", message="404 Not Found"),404
@app.errorhandler(500)
def server_error(error): return render_template("coming_soon.html", message="500 Server Error"),500

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
    print(f"Starting Flask on port {free_port}")
    app.run(debug=True, port=free_port)

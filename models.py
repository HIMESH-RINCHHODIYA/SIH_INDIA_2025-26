import datetime
from extensions import db
from flask_login import UserMixin


# ===========================
# College Model
# ===========================
class College(db.Model):
    __tablename__ = "colleges"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    domain = db.Column(db.String(150), unique=True, nullable=False)
    logo = db.Column(db.String(250), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # Relationships
    users = db.relationship("User", back_populates="college", lazy="dynamic")
    fee_payments = db.relationship("FeePayment", back_populates="college", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint("name", name="uq_colleges_name"),
    )

    def __repr__(self):
        return f"<College id={self.id} name={self.name}>"


# ===========================
# User Model
# ===========================
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True)

    # Login / Auth
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), default="Student")  # Student, Faculty, Admin
    verified = db.Column(db.Boolean, default=False)

    # Academic Info
    enrollment_no = db.Column(db.String(50), unique=True)
    scholar_no = db.Column(db.String(50))
    roll_no = db.Column(db.String(50), unique=True)
    program = db.Column(db.String(100))     # B.Tech, M.Tech
    year = db.Column(db.String(10))         # Stored as string
    branch = db.Column(db.String(100))      # CSE, ECE
    section = db.Column(db.String(20))      # A, B
    class_name = db.Column(db.String(100))  # "B.Tech CSBS 5th SEM"
    admission_date = db.Column(db.Date)

    # Personal Info
    dob = db.Column(db.Date)
    gender = db.Column(db.String(20))
    nationality = db.Column(db.String(50))
    religion = db.Column(db.String(50))
    aadhaar_no = db.Column(db.String(20))
    blood_group = db.Column(db.String(5))
    contact = db.Column(db.String(20))  # 🔄 Used instead of "mobile"
    mother_tongue = db.Column(db.String(50))
    marital_status = db.Column(db.String(20), default="Single")
    samagra_id = db.Column(db.String(50))
    category = db.Column(db.String(50))   # General, OBC, SC, ST
    domicile_state = db.Column(db.String(50))

    # Parents Info
    father_name = db.Column(db.String(150))
    father_name_hindi = db.Column(db.String(150))
    father_mobile = db.Column(db.String(20))
    father_income = db.Column(db.Numeric(12, 2), nullable=True)  # ✅ Nullable numeric
    mother_name = db.Column(db.String(150))
    mother_name_hindi = db.Column(db.String(150))
    mother_mobile = db.Column(db.String(20))
    mother_income = db.Column(db.Numeric(12, 2), nullable=True)  # ✅ Nullable numeric

    # Address
    permanent_address = db.Column(db.Text)
    permanent_city = db.Column(db.String(100))
    permanent_state = db.Column(db.String(100))
    permanent_pin = db.Column(db.String(20))
    local_address = db.Column(db.Text)
    local_city = db.Column(db.String(100))
    local_state = db.Column(db.String(100))
    local_pin = db.Column(db.String(20))

    # Bank Details
    bank_name = db.Column(db.String(100))
    bank_branch = db.Column(db.String(100))
    bank_account_no = db.Column(db.String(50))
    bank_ifsc = db.Column(db.String(20))

    # File uploads
    photo = db.Column(db.String(200))
    id_card = db.Column(db.String(200))
    certificate = db.Column(db.String(200))
    transcript = db.Column(db.String(200))
    signature = db.Column(db.String(200))

    # Relationships
    college = db.relationship("College", back_populates="users")
    attendance_records = db.relationship(
        "Attendance", back_populates="student", cascade="all, delete-orphan", lazy="dynamic"
    )
    fee_payments = db.relationship(
        "FeePayment", back_populates="student", cascade="all, delete-orphan", lazy="dynamic"
    )
    results = db.relationship(
        "Result", back_populates="student", cascade="all, delete-orphan", lazy="dynamic"
    )
    student_courses = db.relationship("StudentCourse", back_populates="student", lazy="dynamic")
    faculty_courses = db.relationship("FacultyCourse", back_populates="faculty", lazy="dynamic")

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"


# ===========================
# Attendance Model
# ===========================
class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # Present / Absent
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    student = db.relationship("User", back_populates="attendance_records")

    __table_args__ = (
        db.Index("ix_attendance_date", "date"),
    )

    def __repr__(self):
        return f"<Attendance student={self.student_id} date={self.date} status={self.status}>"


# ===========================
# Fee Payment Model
# ===========================
class FeePayment(db.Model):
    __tablename__ = "fee_payments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True)

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    razorpay_order_id = db.Column(db.String(100), nullable=True)
    payment_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default="Unpaid")  # Unpaid / Pending / Paid / Failed
    payment_method = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    student = db.relationship("User", back_populates="fee_payments")
    college = db.relationship("College", back_populates="fee_payments")

    def __repr__(self):
        return f"<FeePayment id={self.id} student={self.student_id} amount={self.amount} status={self.status}>"


# ===========================
# Fee Configuration Model
# ===========================
class FeeConfig(db.Model):
    __tablename__ = "fee_configs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    program = db.Column(db.String(100), nullable=True)
    branch = db.Column(db.String(100), nullable=True)
    year = db.Column(db.String(20), nullable=True)
    section = db.Column(db.String(20), nullable=True)

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    last_date = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    def __repr__(self):
        return f"<FeeConfig {self.program}/{self.branch}/{self.year}/{self.section} = {self.amount}>"


# ===========================
# Result / Grades Model
# ===========================
class Result(db.Model):
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    course_code = db.Column(db.String(20), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(10), nullable=False)
    marks = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.String(5), nullable=False)
    approved_by_admin = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    student = db.relationship("User", back_populates="results")

    __table_args__ = (
        db.Index("ix_results_student_semester", "student_id", "semester"),
    )

    def __repr__(self):
        return f"<Result student={self.student_id} course={self.course_code} marks={self.marks} grade={self.grade}>"


# ===========================
# Course Model
# ===========================
class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(150), nullable=False, unique=True)
    course_code = db.Column(db.String(50), nullable=False, unique=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    def __repr__(self):
        return f"<Course id={self.id} code={self.course_code} name={self.course_name}>"


# ===========================
# Student Course Enrollment
# ===========================
class StudentCourse(db.Model):
    __tablename__ = "student_courses"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)

    # Auto link program, branch, year at time of enrollment
    program = db.Column(db.String(100))
    branch = db.Column(db.String(100))
    year = db.Column(db.String(10))

    student = db.relationship("User", back_populates="student_courses")
    course = db.relationship("Course", backref="student_enrollments")

    def __repr__(self):
        return f"<StudentCourse student={self.student_id} course={self.course_id}>"


# ===========================
# Faculty Course Assignment
# ===========================
class FacultyCourse(db.Model):
    __tablename__ = "faculty_courses"

    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)

    # Teaching details
    program = db.Column(db.String(100))
    branch = db.Column(db.String(100))
    year = db.Column(db.String(10))
    is_theory = db.Column(db.Boolean, default=True)  # True = Theory, False = Lab

    faculty = db.relationship("User", back_populates="faculty_courses")
    course = db.relationship("Course", backref="faculty_assignments")

    def __repr__(self):
        return f"<FacultyCourse faculty={self.faculty_id} course={self.course_id} theory={self.is_theory}>"

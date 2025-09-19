from datetime import datetime
from extensions import db
from flask_login import UserMixin

# ========================================================================
# CORRECTED ORDER: All models are now defined before they are referenced
# by a ForeignKey. This resolves all NoReferencedTableError issues.
# All dunder methods (e.g., __tablename__) are also syntactically corrected.
# ========================================================================

# ===========================
# 1. Independent Foundational Models
# ===========================
class College(db.Model):
    __tablename__ = "colleges"
    __table_args__ = (db.UniqueConstraint("name", name="uq_colleges_name"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    domain = db.Column(db.String(150), unique=True, nullable=False)
    logo = db.Column(db.String(250), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    users = db.relationship("User", back_populates="college", lazy="dynamic")
    fee_payments = db.relationship("FeePayment", back_populates="college", lazy="dynamic")

    def __repr__(self):
        return f"<College id={self.id} name={self.name}>"

class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(150), nullable=False, unique=True)
    course_code = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    attendance_records = db.relationship("Attendance", back_populates="course")
    faculty_courses = db.relationship("FacultyCourse", back_populates="course")
    student_enrollments = db.relationship("StudentCourse", back_populates="course")
    results = db.relationship("Result", back_populates="course")

    def __repr__(self):
        return f"<Course id={self.id} code={self.course_code} name={self.course_name}>"

class Program(db.Model):
    __tablename__ = "programs"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    duration_years = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    branches = db.relationship("Branch", back_populates="program", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Program id={self.id} name={self.name}>"

# Branch depends on Program
class Branch(db.Model):
    __tablename__ = "branches"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    program = db.relationship("Program", back_populates="branches")

    def __repr__(self):
        return f"<Branch id={self.id} name={self.name} program_id={self.program_id}>"

class Year(db.Model):
    __tablename__ = "years"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    def __repr__(self):
        return f"<Year id={self.id} name={self.name}>"

class Semester(db.Model):
    __tablename__ = "semesters"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    def __repr__(self):
        return f"<Semester id={self.id} name={self.name}>"

# ===========================
# 2. Core User Model (depends on College)
# ===========================
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True)

    # Login / Auth
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), default="Student")
    verified = db.Column(db.Boolean, default=False)

    # Academic Info
    enrollment_no = db.Column(db.String(50), unique=True)
    scholar_no = db.Column(db.String(50))
    roll_no = db.Column(db.String(50), unique=True)
    program = db.Column(db.String(100))
    year = db.Column(db.String(10))
    branch = db.Column(db.String(100))
    section = db.Column(db.String(20))
    semester = db.Column(db.String(20))
    class_name = db.Column(db.String(100))
    admission_date = db.Column(db.Date)

    # Personal Info
    dob = db.Column(db.Date)
    gender = db.Column(db.String(20))
    nationality = db.Column(db.String(50))
    religion = db.Column(db.String(50))
    aadhaar_no = db.Column(db.String(20))
    blood_group = db.Column(db.String(5))
    contact = db.Column(db.String(20))
    mother_tongue = db.Column(db.String(50))
    marital_status = db.Column(db.String(20), default="Single")
    samagra_id = db.Column(db.String(50))
    category = db.Column(db.String(50))
    domicile_state = db.Column(db.String(50))

    # Parents Info
    father_name = db.Column(db.String(150))
    father_name_hindi = db.Column(db.String(150))
    father_mobile = db.Column(db.String(20))
    father_income = db.Column(db.Numeric(12, 2), nullable=True)
    mother_name = db.Column(db.String(150))
    mother_name_hindi = db.Column(db.String(150))
    mother_mobile = db.Column(db.String(20))
    mother_income = db.Column(db.Numeric(12, 2), nullable=True)

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
    attendance_records = db.relationship("Attendance", back_populates="student", cascade="all, delete-orphan", lazy="dynamic")
    fee_payments = db.relationship("FeePayment", back_populates="student", cascade="all, delete-orphan", lazy="dynamic")
    results = db.relationship("Result", back_populates="student", cascade="all, delete-orphan", lazy="dynamic")
    student_courses = db.relationship("StudentCourse", back_populates="student", lazy="dynamic")
    faculty_courses = db.relationship("FacultyCourse", back_populates="faculty", lazy="dynamic")

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"

# ===========================
# 3. Dependent Models (depend on User, Course, etc.)
# ===========================
class Result(db.Model):
    __tablename__ = "results"
    __table_args__ = (db.Index("ix_results_student_semester", "student_id", "semester"),)

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    semester = db.Column(db.String(10), nullable=False)
    marks = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.String(5), nullable=False)
    approved_by_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = db.relationship("User", back_populates="results")
    course = db.relationship("Course", back_populates="results")

    def __repr__(self):
        return f"<Result student={self.student_id} course={self.course_id} marks={self.marks} grade={self.grade}>"

class Attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    branch = db.Column(db.String(50), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)
    remarks = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("User", back_populates="attendance_records")
    course = db.relationship("Course", back_populates="attendance_records")

    def __repr__(self):
        return f"<Attendance student={self.student_id} course={self.course_id} date={self.date} status={self.status}>"

class FeePayment(db.Model):
    __tablename__ = "fee_payments"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    razorpay_order_id = db.Column(db.String(100))
    payment_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default="Unpaid")
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = db.relationship("User", back_populates="fee_payments")
    college = db.relationship("College", back_populates="fee_payments")

    def __repr__(self):
        return f"<FeePayment id={self.id} student={self.student_id} amount={self.amount} status={self.status}>"

class StudentCourse(db.Model):
    __tablename__ = "student_courses"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    program = db.Column(db.String(100), nullable=True)
    branch = db.Column(db.String(100), nullable=True)
    year = db.Column(db.String(10), nullable=True)
    semester = db.Column(db.String(20), nullable=True)

    student = db.relationship("User", back_populates="student_courses")
    course = db.relationship("Course", back_populates="student_enrollments")

    def __repr__(self):
        return (
            f"<StudentCourse id={self.id} "
            f"student_id={self.student_id} "
            f"course_id={self.course_id} "
            f"semester={self.semester}>"
        )

class FacultyCourse(db.Model):
    __tablename__ = "faculty_courses"
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    program = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(100), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    course_type = db.Column(db.String(20), nullable=False)

    faculty = db.relationship("User", back_populates="faculty_courses")
    course = db.relationship("Course", back_populates="faculty_courses")

    def __repr__(self):
        return f"<FacultyCourse faculty={self.faculty_id} course={self.course_id} sem={self.semester}>"

# ===========================
# 4. Configuration and Utility Models
# ===========================
class FeeConfig(db.Model):
    __tablename__ = "fee_configs"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    program = db.Column(db.String(100))
    branch = db.Column(db.String(100))
    year = db.Column(db.String(20))
    section = db.Column(db.String(20))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    last_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<FeeConfig {self.program}/{self.branch}/{self.year}/{self.section} = {self.amount}>"

class DropdownValue(db.Model):
    __tablename__ = "dropdown_values"
    __table_args__ = (db.UniqueConstraint("field", "value", name="uq_field_value"),)

    id = db.Column(db.Integer, primary_key=True)
    field = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<DropdownValue field={self.field} value={self.value}>"


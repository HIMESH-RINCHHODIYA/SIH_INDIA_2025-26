from flask import render_template, request, redirect, url_for, flash
from faculty_attendance import faculty_stud_bp
from models import User, Attendance, db
from datetime import datetime


# --------- Step 1 & 2: Load Form + Students ---------
@faculty_stud_bp.route('/faculty/attendance', methods=['GET', 'POST'])
def faculty_attendance():
    # Get all distinct branches where students exist
    branches = [b[0] for b in db.session.query(User.branch).filter_by(role="Student").distinct().all()]

    students = []
    selected_branch = None
    selected_date = datetime.today().strftime('%Y-%m-%d')

    if request.method == 'POST' and "load_students" in request.form:
        selected_branch = request.form.get('branch')
        selected_date = request.form.get('date')

        # Fetch students for that branch
        if selected_branch:
            students = User.query.filter_by(branch=selected_branch, role="Student").all()

    return render_template(
        'faculty_stud.html',
        branches=branches,
        students=students,
        selected_branch=selected_branch,
        selected_date=selected_date
    )


# --------- Step 3: Save Attendance ---------
@faculty_stud_bp.route('/faculty/attendance/save', methods=['POST'])
def save_attendance():
    selected_branch = request.form.get('branch')
    selected_date = request.form.get('date')

    try:
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid date format!", "danger")
        return redirect(url_for("faculty_stud_bp.faculty_attendance"))

    # Fetch students for branch
    students = User.query.filter_by(branch=selected_branch, role="Student").all()

    for student in students:
        checkbox_name = f'attendance_{student.id}'
        present = request.form.get(checkbox_name) == "on"

        # Check existing record
        existing = Attendance.query.filter_by(
            student_id=student.id,
            date=selected_date_obj,
            branch=selected_branch
        ).first()

        if existing:
            existing.status = "Present" if present else "Absent"
        else:
            attendance = Attendance(
                student_id=student.id,
                date=selected_date_obj,
                branch=selected_branch,
                class_name=student.year,  # Assuming student.year = class
                status="Present" if present else "Absent"
            )
            db.session.add(attendance)

    db.session.commit()
    flash("✅ Attendance saved successfully!", "success")
    return redirect(url_for("faculty_stud_bp.faculty_attendance", branch=selected_branch, date=selected_date))

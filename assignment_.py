import os, io, zipfile, csv
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, send_file, Response
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

import openpyxl
from openpyxl.styles import Font, Alignment

from extensions import db
from assignment_models import (
    Assignment, AssignmentSubmission, AssignmentQuestion,
    AssignmentOption, AssignmentAnswer, AssignmentAttachment
)
from models import Course, Program, Branch, Year, Semester, StudentCourse


# ========================================================
# BLUEPRINT
# ========================================================
assignment_bp = Blueprint(
    "assignment_bp", __name__,
    template_folder="../templates/assignment_templates"
)


# ========================================================
# ROLE DECORATORS
# ========================================================
def faculty_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role.lower() != "faculty":
            flash("Unauthorized", "danger")
            return redirect(url_for("dashboard"))
        return func(*args, **kwargs)
    return wrapper


def student_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role.lower() != "student":
            flash("Unauthorized", "danger")
            return redirect(url_for("dashboard"))
        return func(*args, **kwargs)
    return wrapper


# ========================================================
# FILE HELPER
# ========================================================
def save_file(file, folder="static/uploads/assignments"):
    if not file:
        return None
    filename = secure_filename(file.filename)
    path = os.path.join(folder, f"{datetime.utcnow().timestamp()}_{filename}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file.save(path)
    return path


# ========================================================
# FACULTY ROUTES
# ========================================================

@assignment_bp.route("/assignments/faculty")
@login_required
@faculty_required
def faculty_assignments():
    """View assignments created by faculty"""
    teaching_courses = [fc.course_id for fc in current_user.faculty_courses]
    assignments = Assignment.query.filter(
        Assignment.created_by == current_user.id,
        Assignment.course_id.in_(teaching_courses)
    ).order_by(Assignment.created_at.desc()).all()
    return render_template("faculty_assignment.html", assignments=assignments)


@assignment_bp.route("/assignments/create", methods=["GET", "POST"])
@login_required
@faculty_required
def create_assignment():
    """Create new assignment with cohort filters"""
    if request.method == "POST":
        new_assignment = Assignment(
            title=request.form.get("title"),
            description=request.form.get("description"),
            deadline=datetime.strptime(request.form.get("deadline"), "%Y-%m-%d"),
            type=request.form.get("type", "file"),
            created_by=current_user.id,
            course_id=request.form.get("course_id"),
            program=request.form.get("program"),
            branch=request.form.get("branch"),
            year=request.form.get("year"),
            semester=request.form.get("semester"),
            section=request.form.get("section"),
        )
        db.session.add(new_assignment)
        db.session.commit()

        # handle attachments
        if request.files.get("file"):
            fpath = save_file(request.files.get("file"))
            db.session.add(AssignmentAttachment(
                assignment_id=new_assignment.id, file_path=fpath
            ))
        if request.form.get("link_url"):
            db.session.add(AssignmentAttachment(
                assignment_id=new_assignment.id, link_url=request.form.get("link_url")
            ))
        db.session.commit()

        flash("Assignment created successfully!", "success")
        return redirect(url_for("assignment_bp.edit_assignment", assignment_id=new_assignment.id))

    # Provide dropdowns
    teaching_courses = [fc.course for fc in current_user.faculty_courses]
    return render_template(
        "assignment_create.html",
        courses=teaching_courses,
        programs=Program.query.all(),
        branches=Branch.query.all(),
        years=Year.query.all(),
        semesters=Semester.query.all()
    )


@assignment_bp.route("/assignments/<int:assignment_id>/edit", methods=["GET", "POST"])
@login_required
@faculty_required
def edit_assignment(assignment_id):
    """Add assignment questions / options"""
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.created_by != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("assignment_bp.faculty_assignments"))

    if request.method == "POST":
        q = AssignmentQuestion(
            assignment_id=assignment.id,
            question_text=request.form.get("question_text"),
            question_type=request.form.get("question_type"),
            points=int(request.form.get("points", 1)),
            required=bool(request.form.get("required"))
        )
        db.session.add(q)
        db.session.commit()

        # Options for MCQ / Multi / TrueFalse
        if q.question_type in ["mcq", "multi", "truefalse"]:
            options = request.form.getlist("options[]")
            corrects = request.form.getlist("correct[]")
            for i, otext in enumerate(options):
                db.session.add(AssignmentOption(
                    question_id=q.id,
                    option_text=otext,
                    is_correct=str(i) in corrects
                ))
            db.session.commit()

        flash("Question added", "success")
        return redirect(url_for("assignment_bp.edit_assignment", assignment_id=assignment.id))

    questions = AssignmentQuestion.query.filter_by(assignment_id=assignment.id).all()
    return render_template("faculty_edit_assignment.html", assignment=assignment, questions=questions)


@assignment_bp.route("/assignments/<int:assignment_id>/delete_question/<int:qid>", methods=["POST"])
@login_required
@faculty_required
def delete_question(assignment_id, qid):
    """Delete a question"""
    assignment = Assignment.query.get_or_404(assignment_id)
    q = AssignmentQuestion.query.get_or_404(qid)
    if assignment.created_by != current_user.id:
        flash("Unauthorized delete", "danger")
        return redirect(url_for("assignment_bp.edit_assignment", assignment_id=assignment.id))
    db.session.delete(q)
    db.session.commit()
    flash("Question deleted", "success")
    return redirect(url_for("assignment_bp.edit_assignment", assignment_id=assignment.id))


@assignment_bp.route("/assignments/<int:assignment_id>/submissions")
@login_required
@faculty_required
def view_submissions(assignment_id):
    """Faculty view all submissions"""
    assignment = Assignment.query.get_or_404(assignment_id)
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).all()

    numeric_scores = []
    for s in submissions:
        if s.grade and "/" in s.grade:
            try:
                numeric_scores.append(int(s.grade.split("/")[0]))
            except ValueError:
                pass
    avg_score = round(sum(numeric_scores)/len(numeric_scores), 2) if numeric_scores else None

    return render_template("faculty_submissions.html", assignment=assignment, submissions=submissions, avg_score=avg_score)


@assignment_bp.route("/assignments/submission/<int:sub_id>/grade", methods=["POST"])
@login_required
@faculty_required
def grade_submission(sub_id):
    """Manual grading"""
    submission = AssignmentSubmission.query.get_or_404(sub_id)
    submission.grade = request.form.get("grade")
    submission.feedback = request.form.get("feedback")
    submission.graded_at = datetime.utcnow()
    db.session.commit()
    flash(f"Grade saved for {submission.student.name}", "success")
    return redirect(url_for("assignment_bp.view_submissions", assignment_id=submission.assignment_id))


@assignment_bp.route("/assignments/submission/<int:sub_id>/auto_grade", methods=["POST"])
@login_required
@faculty_required
def auto_grade_submission(sub_id):
    """Auto-grade objective questions"""
    submission = AssignmentSubmission.query.get_or_404(sub_id)
    assignment = Assignment.query.get(submission.assignment_id)
    questions = AssignmentQuestion.query.filter_by(assignment_id=assignment.id).all()

    score, total_points = 0, 0
    for q in questions:
        total_points += q.points
        ans = AssignmentAnswer.query.filter_by(submission_id=submission.id, question_id=q.id).first()
        if not ans: continue

        if q.question_type == "truefalse":
            correct = [opt for opt in q.options if opt.is_correct]
            if correct and ans.answer_text == correct[0].option_text:
                score += q.points
        elif q.question_type in ["mcq", "multi"]:
            correct_ids = [str(opt.id) for opt in q.options if opt.is_correct]
            submitted = ans.selected_options.split(",") if ans.selected_options else []
            if set(correct_ids) == set(submitted):
                score += q.points

    submission.grade = f"{score}/{total_points}"
    submission.graded_at = datetime.utcnow()
    db.session.commit()
    flash(f"Auto-graded: {submission.student.name} scored {submission.grade}", "info")
    return redirect(url_for("assignment_bp.view_submissions", assignment_id=assignment.id))


# ========================================================
# STUDENT ROUTES
# ========================================================

@assignment_bp.route("/assignments/student")
@login_required
@student_required
def student_assignments():
    """List assignments for student with cohort filter"""
    enrolled = [sc.course_id for sc in current_user.student_courses]
    assignments = Assignment.query.filter(
        Assignment.course_id.in_(enrolled),
        Assignment.program == current_user.program,
        Assignment.branch == current_user.branch,
        Assignment.year == current_user.year,
        Assignment.semester == current_user.semester,
        Assignment.section == current_user.section
    ).order_by(Assignment.deadline.asc()).all()

    subs = {s.assignment_id: s for s in AssignmentSubmission.query.filter_by(student_id=current_user.id).all()}
    return render_template("student_assignment.html", assignments=assignments, submissions=subs, now=datetime.utcnow)


@assignment_bp.route("/assignments/<int:assignment_id>/take", methods=["GET", "POST"])
@login_required
@student_required
def take_assignment(assignment_id):
    """Take an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    questions = AssignmentQuestion.query.filter_by(assignment_id=assignment.id).all()
    attachments = AssignmentAttachment.query.filter_by(assignment_id=assignment.id).all()

    if request.method == "POST":
        sub = AssignmentSubmission(assignment_id=assignment.id, student_id=current_user.id)
        db.session.add(sub)
        db.session.flush()

        for q in questions:
            ans_text = request.form.get(f"q_{q.id}")
            selected_opts = request.form.getlist(f"opt_{q.id}")
            file = request.files.get(f"file_{q.id}")
            db.session.add(AssignmentAnswer(
                submission_id=sub.id,
                question_id=q.id,
                answer_text=ans_text,
                selected_options=",".join(selected_opts) if selected_opts else None,
                file_path=save_file(file, "static/uploads/answers") if file else None
            ))
        db.session.commit()
        flash("Assignment submitted successfully!", "success")
        return redirect(url_for("assignment_bp.student_assignments"))

    return render_template("student_take_assignment.html", assignment=assignment, questions=questions, attachments=attachments)


# ========================================================
# EXPORTS / DOWNLOADS
# ========================================================

@assignment_bp.route("/assignments/<int:assignment_id>/download_zip")
@login_required
@faculty_required
def download_submissions_zip(assignment_id):
    """Download all student submissions as ZIP"""
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for sub in submissions:
            student_folder = sub.student.name.replace(" ", "_")

            # Files
            for ans in sub.answers:
                if ans.file_path and os.path.exists(ans.file_path):
                    zf.write(ans.file_path, f"{student_folder}/Q{ans.question_id}_{os.path.basename(ans.file_path)}")

            # Summary
            summary = f"Student: {sub.student.name}\nSubmitted: {sub.submitted_at}\nGrade: {sub.grade or 'Pending'}\nFeedback: {sub.feedback or '—'}\n\n"
            for ans in sub.answers:
                summary += f"Q{ans.question_id}: {ans.question.question_text}\n"
                if ans.answer_text: summary += f"  Answer: {ans.answer_text}\n"
                if ans.selected_option_texts: summary += f"  Selected: {', '.join(ans.selected_option_texts)}\n"
                if ans.file_path: summary += f"  File: {os.path.basename(ans.file_path)}\n"
                summary += "\n"
            zf.writestr(f"{student_folder}/SUMMARY.txt", summary)

    memory_file.seek(0)
    return send_file(memory_file, download_name="submissions.zip", as_attachment=True)


@assignment_bp.route("/assignments/<int:assignment_id>/export_csv")
@login_required
@faculty_required
def export_grades_csv(assignment_id):
    """Export grades+answers as CSV"""
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student","Submitted At","Grade","Feedback","Question ID","Question Text","Answer","Selected","File"])
    for sub in submissions:
        for ans in sub.answers:
            writer.writerow([
                sub.student.name,
                sub.submitted_at.strftime('%Y-%m-%d %H:%M'),
                sub.grade or "", sub.feedback or "",
                ans.question.id, ans.question.question_text,
                ans.answer_text or "",
                ", ".join(ans.selected_option_texts) if ans.selected_option_texts else "",
                ans.file_path or ""
            ])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=grades_{assignment_id}.csv"})


@assignment_bp.route("/assignments/<int:assignment_id>/export_xlsx")
@login_required
@faculty_required
def export_grades_xlsx(assignment_id):
    """Export grades+answers as Excel"""
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()
    wb = openpyxl.Workbook(); ws = wb.active; ws.title="Results"

    headers = ["Student","Submitted At","Grade","Feedback","Question ID","Question Text","Answer","Selected","File"]
    ws.append(headers)
    for col in ws[1]:
        col.font = Font(bold=True); col.alignment = Alignment(horizontal="center")

    for sub in submissions:
        for ans in sub.answers:
            ws.append([
                sub.student.name,
                sub.submitted_at.strftime('%Y-%m-%d %H:%M'),
                sub.grade or "", sub.feedback or "",
                ans.question.id, ans.question.question_text,
                ans.answer_text or "",
                ", ".join(ans.selected_option_texts) if ans.selected_option_texts else "",
                os.path.basename(ans.file_path) if ans.file_path else ""
            ])

    for col in ws.columns:
        max_len = max((len(str(cell.value)) for cell in col if cell.value), default=10)
        ws.column_dimensions[col[0].column_letter].width = max_len + 2

    memory_file = io.BytesIO(); wb.save(memory_file); memory_file.seek(0)
    return send_file(memory_file, download_name=f"grades_{assignment_id}.xlsx", as_attachment=True,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    
    
@assignment_bp.route("/assignments/<int:assignment_id>/download_student/<int:sub_id>")
@login_required
@faculty_required
def download_student_submission(assignment_id, sub_id):
    """Download one student's submission as ZIP"""
    submission = AssignmentSubmission.query.filter_by(
        id=sub_id, assignment_id=assignment_id
    ).first_or_404()

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        student_folder = submission.student.name.replace(" ", "_")

        # files
        for ans in submission.answers:
            if ans.file_path and os.path.exists(ans.file_path):
                arcname = f"{student_folder}/Q{ans.question_id}_{os.path.basename(ans.file_path)}"
                zf.write(ans.file_path, arcname)

        # summary text
        summary = f"Student: {submission.student.name}\n"
        summary += f"Submitted At: {submission.submitted_at}\n"
        summary += f"Grade: {submission.grade or 'Not graded'}\n"
        summary += f"Feedback: {submission.feedback or '—'}\n\n"
        for ans in submission.answers:
            summary += f"Q{ans.question_id}: {ans.question.question_text}\n"
            if ans.answer_text:
                summary += f"  Answer: {ans.answer_text}\n"
            if ans.selected_option_texts:
                summary += f"  Selected Options: {', '.join(ans.selected_option_texts)}\n"
            if ans.file_path:
                summary += f"  File: {os.path.basename(ans.file_path)}\n"
            summary += "\n"

        zf.writestr(f"{student_folder}/SUMMARY.txt", summary)

    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name=f"submission_{submission.student.name.replace(' ', '_')}.zip",
        as_attachment=True
    )    
    
    
@assignment_bp.route("/assignments/<int:assignment_id>/delete", methods=["POST"])
@login_required
@faculty_required
def delete_assignment(assignment_id):
    """Faculty can delete an assignment (with all questions, answers, attachments)."""
    assignment = Assignment.query.get_or_404(assignment_id)

    # Ensure only creator can delete
    if assignment.created_by != current_user.id:
        flash("❌ Unauthorized - you can only delete your own assignments", "danger")
        return redirect(url_for("assignment_bp.faculty_assignments"))

    try:
        # Delete all related submissions (cascade will handle answers)
        for attachment in AssignmentAttachment.query.filter_by(assignment_id=assignment.id).all():
            db.session.delete(attachment)

        # Delete assignment
        db.session.delete(assignment)
        db.session.commit()
        flash("🗑 Assignment deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"⚠️ Error deleting assignment: {str(e)}", "danger")

    return redirect(url_for("assignment_bp.faculty_assignments"))    
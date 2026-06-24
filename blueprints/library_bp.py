# ==========================================
# Library Blueprint (Books + Digital Resources + Reports)
# ==========================================

import os
from datetime import datetime

from flask import (Blueprint, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy import or_   # ✅ FIXED: you need this for search_students

from extensions import db
from library_models import Book, BorrowRecord, DigitalResource, Penalty
from models import User

library_bp = Blueprint(
    "library_bp", __name__, template_folder="../templates/library_templates"
)

# ---------------- Config ---------------- #
UPLOADS_DIR = "static/uploads/library"
os.makedirs(UPLOADS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "epub", "txt"}


def allowed_file(filename):
    """Helper check for valid extensions"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# =====================
# Student / Admin Dashboard
# =====================
@library_bp.route("/library")
@login_required
def library_dashboard():
    if current_user.role == "Student":
        borrows = BorrowRecord.query.filter_by(user_id=current_user.id).all()
        penalties = (
            Penalty.query.join(BorrowRecord)
            .filter(BorrowRecord.user_id == current_user.id)
            .all()
        )
        return render_template(
            "library_dashboard.html",
            borrows=borrows,
            penalties=penalties,
            now=datetime.utcnow,
        )

    elif current_user.role == "Admin":
        books = Book.query.order_by(Book.title.asc()).all()
        return render_template("library_books.html", books=books)

    flash("❌ Unauthorized access!", "danger")
    return redirect(url_for("dashboard"))


# =====================
# Admin: Add Book
# =====================
@library_bp.route("/library/add", methods=["GET", "POST"])
@login_required
def add_book():
    if current_user.role != "Admin":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        isbn = request.form.get("isbn")
        category = request.form.get("category")
        year = request.form.get("year")
        copies = int(request.form.get("copies_total", 1))

        book = Book(
            title=title,
            author=author,
            isbn=isbn,
            category=category,
            year=year,
            copies_total=copies,
            copies_available=copies,
        )
        db.session.add(book)
        db.session.commit()

        flash("✅ Book added successfully!", "success")
        return redirect(url_for("library_bp.library_dashboard"))

    return render_template("add_book.html")


# =====================
# Admin: Edit Book
# =====================
@library_bp.route("/library/edit/<int:book_id>", methods=["POST"])
@login_required
def edit_book(book_id):
    if current_user.role != "Admin":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("dashboard"))

    book = Book.query.get_or_404(book_id)
    book.title = request.form.get("title")
    book.author = request.form.get("author")
    book.category = request.form.get("category")
    new_total = int(request.form.get("copies_total", book.copies_total))

    diff = new_total - book.copies_total
    book.copies_total = new_total
    book.copies_available = max(0, book.copies_available + diff)

    db.session.commit()
    flash("✅ Book updated successfully!", "success")
    return redirect(url_for("library_bp.library_dashboard"))


# =====================
# Admin: Delete Book
# =====================
@library_bp.route("/library/delete/<int:book_id>")
@login_required
def delete_book(book_id):
    if current_user.role != "Admin":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("dashboard"))

    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()

    flash("🗑️ Book deleted successfully", "info")
    return redirect(url_for("library_bp.library_dashboard"))


# =====================
# Admin: Issue Book
# =====================
@library_bp.route("/library/issue/<int:book_id>", methods=["POST"])
@login_required
def issue_book(book_id):
    if current_user.role != "Admin":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("dashboard"))

    user_id = request.form.get("user_id")
    if not user_id:
        flash("❌ No student selected", "danger")
        return redirect(url_for("library_bp.library_dashboard"))

    student = User.query.get(user_id)
    if not student or student.role != "Student":
        flash("❌ Invalid student", "danger")
        return redirect(url_for("library_bp.library_dashboard"))

    book = Book.query.get_or_404(book_id)
    if book.copies_available < 1:
        flash("❌ No copies available", "danger")
        return redirect(url_for("library_bp.library_dashboard"))

    borrow = BorrowRecord(user_id=student.id, book_id=book.id)
    book.copies_available -= 1
    db.session.add(borrow)
    db.session.commit()

    flash(f"📖 '{book.title}' issued to {student.name}", "success")
    return redirect(url_for("library_bp.library_dashboard"))


# =====================
# Admin: Return Book
# =====================
@library_bp.route("/library/return/<int:borrow_id>")
@login_required
def return_book(borrow_id):
    if current_user.role != "Admin":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("dashboard"))

    borrow = BorrowRecord.query.get_or_404(borrow_id)
    borrow.return_date = datetime.utcnow()

    if borrow.return_date > borrow.due_date:
        days = (borrow.return_date - borrow.due_date).days
        fine = days * 5.0
        penalty = Penalty(borrow_id=borrow.id, amount=fine, penalty_type="per_day")
        db.session.add(penalty)

    borrow.book.copies_available += 1
    db.session.commit()
    flash("✅ Book returned successfully", "success")
    return redirect(url_for("library_bp.library_dashboard"))


# =====================
# Student: Catalog
# =====================
@library_bp.route("/library/catalog")
@login_required
def library_catalog():
    q = request.args.get("q", "")
    if q:
        books = Book.query.filter(
            (Book.title.ilike(f"%{q}%"))
            | (Book.author.ilike(f"%{q}%"))
            | (Book.isbn.ilike(f"%{q}%"))
            | (Book.category.ilike(f"%{q}%"))
        ).all()
    else:
        books = Book.query.all()

    return render_template("library_catalog.html", books=books, q=q)


# =====================
# Admin: Upload Digital Resource
# =====================
@library_bp.route("/library/upload", methods=["GET", "POST"])
@login_required
def upload_resource():
    if current_user.role != "Admin":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form.get("title")
        desc = request.form.get("description")
        category = request.form.get("category")

        file = request.files.get("file")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(UPLOADS_DIR, filename)
            file.save(save_path)

            resource = DigitalResource(
                title=title,
                description=desc,
                category=category,
                file_path=f"{UPLOADS_DIR}/{filename}",
                uploaded_by=current_user.id,
            )
            db.session.add(resource)
            db.session.commit()
            flash("✅ Resource uploaded successfully", "success")
            return redirect(url_for("library_bp.list_resources"))
        else:
            flash("❌ Invalid file type (Use PDF/EPUB/TXT)", "danger")

    return render_template("upload_resource.html")


# =====================
# Students + Admin: View Resources
# =====================
@library_bp.route("/library/resources")
@login_required
def list_resources():
    query = DigitalResource.query
    category = request.args.get("category")
    branch = request.args.get("branch")
    year = request.args.get("year")
    semester = request.args.get("semester")

    if category:
        query = query.filter(DigitalResource.category.ilike(f"%{category}%"))
    if branch:
        query = query.filter(DigitalResource.category.ilike(f"%{branch}%"))
    if year:
        query = query.filter(DigitalResource.category.ilike(f"%{year}%"))
    if semester:
        query = query.filter(DigitalResource.category.ilike(f"%{semester}%"))

    resources = query.order_by(DigitalResource.uploaded_on.desc()).all()
    branches = [b[0] for b in db.session.query(User.branch).distinct().all() if b[0]]
    years = [y[0] for y in db.session.query(User.year).distinct().all() if y[0]]
    semesters = [s[0] for s in db.session.query(User.semester).distinct().all() if s[0]]

    return render_template(
        "library_resources.html",
        resources=resources,
        branches=branches,
        years=years,
        semesters=semesters,
    )


# =====================
# Admin: Reports
# =====================
@library_bp.route("/library/reports")
@login_required
def library_reports():
    if current_user.role != "Admin":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("dashboard"))

    most_borrowed = (
        db.session.query(Book.title, db.func.count(BorrowRecord.id))
        .join(BorrowRecord)
        .group_by(Book.id)
        .all()
    )
    overdue = BorrowRecord.query.filter(
        BorrowRecord.return_date == None, BorrowRecord.due_date < datetime.utcnow()
    ).all()
    penalties = Penalty.query.all()

    return render_template(
        "library_reports.html",
        most_borrowed=most_borrowed,
        overdue=overdue,
        penalties=penalties,
    )


# =====================
# AJAX: Search Students
# =====================
@library_bp.route("/library/search_students")
@login_required
def search_students():
    if current_user.role != "Admin":
        return {"results": []}

    q = request.args.get("q", "").strip()
    if not q:
        return {"results": []}

    students = User.query.filter(
        User.role == "Student",
        or_(
            User.name.ilike(f"%{q}%"),
            User.enrollment_no.ilike(f"%{q}%"),
            User.roll_no.ilike(f"%{q}%"),
        ),
    ).limit(10).all()

    results = [
        {"id": s.id, "text": f"{s.name} | {s.roll_no or ''} | {s.enrollment_no or ''}"}
        for s in students
    ]
    return {"results": results}
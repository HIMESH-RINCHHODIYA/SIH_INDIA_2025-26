from datetime import datetime, timedelta

from extensions import db
from models import User


class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255))
    isbn = db.Column(db.String(50), unique=True)
    category = db.Column(db.String(100))
    year = db.Column(db.Integer)
    copies_total = db.Column(db.Integer, default=1)
    copies_available = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f"<Book {self.title}>"


class BorrowRecord(db.Model):
    __tablename__ = "borrow_records"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(
        db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=14)
    )
    return_date = db.Column(db.DateTime, nullable=True)
    user = db.relationship("User", backref="borrowed_books")
    book = db.relationship("Book", backref="borrow_records")

    def is_overdue(self):
        return self.return_date is None and datetime.utcnow() > self.due_date


class Penalty(db.Model):
    __tablename__ = "penalties"
    id = db.Column(db.Integer, primary_key=True)
    borrow_id = db.Column(db.Integer, db.ForeignKey("borrow_records.id"))
    amount = db.Column(db.Float, nullable=False)
    penalty_type = db.Column(db.String(50))  # e.g. per_day
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    borrow = db.relationship("BorrowRecord", backref="penalties")


class Reservation(db.Model):
    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    reserved_on = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(
        db.String(20), default="Pending"
    )  # Pending, Fulfilled, Cancelled
    user = db.relationship("User", backref="reservations")
    book = db.relationship("Book", backref="reservations")


# 🔥 ADD THIS CLASS
class DigitalResource(db.Model):
    __tablename__ = "digital_resources"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)  # store relative file path
    category = db.Column(db.String(100))
    uploaded_on = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    user = db.relationship("User", backref="uploaded_resources")

    def __repr__(self):
        return f"<DigitalResource {self.title}>"

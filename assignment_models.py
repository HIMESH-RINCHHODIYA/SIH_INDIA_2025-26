from datetime import datetime
from extensions import db

class Assignment(db.Model):
    __tablename__ = "assignments"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(50), default="file")  # file, quiz, hybrid
    deadline = db.Column(db.DateTime, nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)

    program = db.Column(db.String(100))
    branch = db.Column(db.String(100))
    year = db.Column(db.String(10))
    semester = db.Column(db.String(20))
    section = db.Column(db.String(20))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    faculty = db.relationship("User", backref="assignments_created")
    course = db.relationship("Course", backref="assignments")


class AssignmentAttachment(db.Model):
    __tablename__ = "assignment_attachments"
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"))
    file_path = db.Column(db.String(255))
    link_url = db.Column(db.String(255))


class AssignmentQuestion(db.Model):
    __tablename__ = "assignment_questions"
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"))
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # mcq, multi, short, long, truefalse, file
    points = db.Column(db.Integer, default=1)
    required = db.Column(db.Boolean, default=False)

    options = db.relationship(
        "AssignmentOption",
        backref="question",
        cascade="all, delete-orphan"
    )


class AssignmentOption(db.Model):
    __tablename__ = "assignment_options"
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("assignment_questions.id"))
    option_text = db.Column(db.String(255))
    is_correct = db.Column(db.Boolean, default=False)


class AssignmentSubmission(db.Model):
    __tablename__ = "assignment_submissions"
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"))
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    grade = db.Column(db.String(10))
    feedback = db.Column(db.Text)
    graded_at = db.Column(db.DateTime)

    assignment = db.relationship("Assignment", backref="submissions")
    student = db.relationship("User", backref="assignment_submissions")
    answers = db.relationship("AssignmentAnswer", backref="submission", cascade="all, delete-orphan")


class AssignmentAnswer(db.Model):
    __tablename__ = "assignment_answers"
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("assignment_submissions.id"))
    question_id = db.Column(db.Integer, db.ForeignKey("assignment_questions.id"))
    answer_text = db.Column(db.Text)
    selected_options = db.Column(db.String)  # comma-separated IDs
    file_path = db.Column(db.String)

    question = db.relationship("AssignmentQuestion", backref="answers")

    @property
    def selected_option_texts(self):
        if not self.selected_options:
            return []
        ids = [int(x) for x in self.selected_options.split(",") if x]
        return [opt.option_text for opt in self.question.options if opt.id in ids]
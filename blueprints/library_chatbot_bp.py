# ==========================================
# Library Chatbot Blueprint (Hybrid Mode)
# ==========================================

import os

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required
from openai import OpenAI

from extensions import db
from library_models import Book, DigitalResource
from models import User

# Initialize OpenAI client (may fail if key invalid/quota over)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chatbot_bp = Blueprint(
    "chatbot_bp", __name__, template_folder="../templates/library_templates"
)


# ===========
# ROUTES
# ===========


@chatbot_bp.route("/library/chatbot")
@login_required
def chatbot_page():
    """Render chatbot UI page for both students and admins."""
    return render_template("library_chatbot.html")


@chatbot_bp.route("/library/chatbot/ask", methods=["POST"])
@login_required
def chatbot_ask():
    """Endpoint to handle chatbot questions with fallback."""

    user_input = request.json.get("message", "").lower()

    # --- Step 1: DB Query ---
    books_query = Book.query

    # Basic keyword match
    if "ai" in user_input or "artificial intelligence" in user_input:
        books_query = books_query.filter(
            (Book.title.ilike("%AI%")) | (Book.category.ilike("%AI%"))
        )
    elif "data science" in user_input:
        books_query = books_query.filter(
            (Book.title.ilike("%Data Science%"))
            | (Book.category.ilike("%Data Science%"))
        )
    elif "machine learning" in user_input:
        books_query = books_query.filter(
            (Book.title.ilike("%Machine Learning%")) | (Book.category.ilike("%ML%"))
        )

    # Optionally filter by student's academic context
    if current_user.branch:
        books_query = books_query.filter(
            Book.category.ilike(f"%{current_user.branch}%")
        )
    if current_user.year:
        books_query = books_query.filter(Book.category.ilike(f"%{current_user.year}%"))
    if current_user.semester:
        books_query = books_query.filter(
            Book.category.ilike(f"%{current_user.semester}%")
        )

    results = books_query.limit(5).all()
    digital_results = DigitalResource.query.limit(5).all()

    # Format result text
    result_text = ""
    if results:
        result_text += "📚 Matching Books:\n"
        for b in results:
            result_text += f"- {b.title} by {b.author} [Available: {b.copies_available}/{b.copies_total}]\n"
    if digital_results:
        result_text += "\n💻 Digital Resources:\n"
        for d in digital_results:
            link = f"/{d.file_path}" if d.file_path else "#"
            result_text += f"- {d.title} ({d.category}) → [Open]({link})\n"
    if not result_text:
        result_text = "No related books/resources found in our records."

    # --- Step 2: Try AI (if working) ---
    system_prompt = """You are a helpful AI Library Assistant for a college ERP.
    - Answer about books/resources, including branch/year/semester context.
    - Use emojis + bullet points.
    - If DB results are given, weave them into your reply.
    """

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
                {"role": "system", "content": f"DB Results:\n{result_text}"},
            ],
            max_tokens=300,
            temperature=0.6,
        )
        ai_answer = completion.choices[0].message.content

    except Exception as e:
        current_app.logger.warning(f"Chatbot AI fallback: {e}")
        ai_answer = f"⚠️ AI is currently unavailable (quota/connection issue).\n\nHere’s what I found from DB:\n\n{result_text}"

    return jsonify({"reply": ai_answer})

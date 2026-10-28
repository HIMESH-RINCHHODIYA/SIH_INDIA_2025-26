# 🎓 ERP-Based Integrated Student Management System (SIH25103)

A Smart Automation ERP system for colleges & universities.

## 🚀 Features
- Student Registration & Login
- School/Department Selection
- AI-Based Timetable (NEP 2020)
- Remote Classroom for Rural Colleges
- AI Dropout Prediction & Counseling
- Online Assessment with Proctoring

## ⚙️ Tech Stack
- Backend: Flask (Python)
- Database: SQLite/MySQL
- Frontend: HTML, CSS, JS
- AI/ML: Scikit-learn, OpenCV

## 📂 Setup
```bash
cd erp-student-management/backend
pip install -r requirements.txt
python app.py
```

## Vercel deployment

Set `DATABASE_URL`, `SECRET_KEY`, and `OPENAI_API_KEY` in the Vercel project
environment settings. Vercel's filesystem is temporary: without `DATABASE_URL`,
the app uses a SQLite database under `/tmp` so the function can start, but that
database is not persistent. The SuperAdmin-managed default logo is stored in
the configured database, so use a managed database for production data. Keep
`.env` local and do not commit it.

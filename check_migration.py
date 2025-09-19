import sqlite3  # or change to psycopg2 / pymysql if using Postgres/MySQL

# ---------- Configuration ----------
DB_PATH = "dev.db"  # SQLite file path, change to your DB URL if using another DB

# Tables to check
tables = {
    "faculty_courses": [
        ("id", False),
        ("faculty_id", False),
        ("course_id", False),
        ("semester", False),
        ("course_type", False),
        ("assigned_at", True),
        ("program", False),
        ("branch", False),
        ("year", False),
    ],
    "student_courses": [
        ("id", False),
        ("student_id", False),
        ("course_id", False),
        ("semester", False),
        ("enrolled_at", True),
        ("program", False),
        ("branch", False),
        ("year", False),
    ],
}

# ---------- Connect ----------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ---------- Check tables and columns ----------
for table_name, columns in tables.items():
    print(f"\nChecking table: {table_name}")
    cursor.execute(f"PRAGMA table_info({table_name})")
    info = cursor.fetchall()
    if not info:
        print("  ❌ Table does not exist!")
        continue
    col_dict = {col[1]: col[3] == 0 for col in info}  # 3 = notnull, 0 means nullable
    for col_name, not_nullable in columns:
        if col_name not in col_dict:
            print(f"  ❌ Missing column: {col_name}")
        else:
            if not_nullable and col_dict[col_name]:
                print(f"  ✅ Column {col_name} exists and is NOT NULL")
            elif not_nullable and not col_dict[col_name]:
                print(f"  ⚠ Column {col_name} exists but NULLABLE")
            else:
                print(f"  ✅ Column {col_name} exists (nullable allowed)")

    # Print a small sample of data
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
    rows = cursor.fetchall()
    print(f"  Sample data ({len(rows)} rows): {rows}")

conn.close()

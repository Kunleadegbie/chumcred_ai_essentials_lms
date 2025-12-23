import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "chumcred_lms.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

# services/db.py (add these)

def ensure_users_cohort_column():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in cur.fetchall()]  # column names

    if "cohort" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN cohort TEXT DEFAULT 'Cohort 1'")

    conn.commit()
    conn.close()


    # PROGRESS (SINGLE SOURCE OF TRUTH)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        week INTEGER NOT NULL,
        status TEXT NOT NULL,
        UNIQUE(user_id, week),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # ASSIGNMENTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        week INTEGER NOT NULL,
        file_path TEXT,
        submitted_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # CERTIFICATES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        issued_at TEXT,
        certificate_path TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


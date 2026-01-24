
# services/db.py
# services/db.py
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("LMS_DB_PATH", "chumcred_lms.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def read_conn():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def write_txn():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with write_txn() as conn:
        cur = conn.cursor()

        # USERS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash BLOB,
            role TEXT DEFAULT 'student'
        )
        """)

        # PROGRESS (Week 0 included)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            user_id INTEGER,
            week INTEGER,
            status TEXT DEFAULT 'locked',
            UNIQUE(user_id, week)
        )
        """)

        # ASSIGNMENTS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            week INTEGER,
            file_path TEXT,
            status TEXT DEFAULT 'submitted',
            grade INTEGER,
            submitted_at TEXT
        )
        """)

        # SUPPORT / HELP
        cur.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            message TEXT,
            admin_reply TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT
        )
        """)

        # BROADCASTS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            message TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """)

# ---------------- BROADCASTS ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            message TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT
       )
       """)

        # Defensive migration (Railway-safe)
        cur.execute("PRAGMA table_info(broadcasts)")
        cols = [row[1] for row in cur.fetchall()]
        if "subject" not in cols:
            cur.execute("ALTER TABLE broadcasts ADD COLUMN subject TEXT")


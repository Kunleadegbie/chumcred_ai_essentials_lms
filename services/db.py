
# services/db.py
# services/db.py
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("LMS_DB_PATH", "chumcred_lms.db")

print("USING DATABASE:", DB_PATH)


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


# ------------------------------------------------
# HELPERS
# ------------------------------------------------

def _column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return column in [r[1] for r in cur.fetchall()]


def _safe_add_column(cur, table, col_def):
    col = col_def.split()[0]

    if not _column_exists(cur, table, col):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
        except Exception:
            pass


# ------------------------------------------------
# INIT / MIGRATION
# ------------------------------------------------

def init_db():

    with write_txn() as conn:
        cur = conn.cursor()

        # ================= USERS =================

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash BLOB,
            role TEXT DEFAULT 'student',
            cohort TEXT DEFAULT 'Cohort 1',
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """)

        # Safe migrations
        _safe_add_column(cur, "users", "email TEXT")
        _safe_add_column(cur, "users", "password_hash BLOB")
        _safe_add_column(cur, "users", "role TEXT DEFAULT 'student'")
        _safe_add_column(cur, "users", "cohort TEXT DEFAULT 'Cohort 1'")
        _safe_add_column(cur, "users", "active INTEGER DEFAULT 1")
        _safe_add_column(cur, "users", "created_at TEXT")


        # ================= PROGRESS =================

        cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            user_id INTEGER,
            week INTEGER,
            status TEXT DEFAULT 'locked',
            UNIQUE(user_id, week)
        )
        """)


        # ================= ASSIGNMENTS =================

        cur.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            week INTEGER,
            file_path TEXT,
            status TEXT DEFAULT 'submitted',
            grade INTEGER,
            feedback TEXT,
            submitted_at TEXT,
            reviewed_at TEXT
        )
        """)

        _safe_add_column(cur, "assignments", "feedback TEXT")
        _safe_add_column(cur, "assignments", "reviewed_at TEXT")


        # ================= SUPPORT =================

        cur.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            message TEXT,
            admin_reply TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT,
            replied_at TEXT
        )
        """)

        _safe_add_column(cur, "support_tickets", "subject TEXT")
        _safe_add_column(cur, "support_tickets", "admin_reply TEXT")
        _safe_add_column(cur, "support_tickets", "replied_at TEXT")


        # ================= BROADCAST =================

        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            message TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """)

        _safe_add_column(cur, "broadcasts", "subject TEXT")
        _safe_add_column(cur, "broadcasts", "active INTEGER DEFAULT 1")


        # ================= CERTIFICATES =================

        cur.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            issued_at TEXT,
            certificate_path TEXT
        )
        """)

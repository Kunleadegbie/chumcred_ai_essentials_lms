
# services/db.py
# services/db.py
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("LMS_DB_PATH", "chumcred_lms.db")
print("USING DB:", DB_PATH)


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


def _column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols


def init_db():
    with write_txn() as conn:
        cur = conn.cursor()

        # ================= USERS =================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash BLOB,
            role TEXT DEFAULT 'student'
        )
        """)

        # ---- MIGRATIONS (SAFE) ----

        if not _column_exists(cur, "users", "cohort"):
            try:
                cur.execute(
                    "ALTER TABLE users ADD COLUMN cohort TEXT DEFAULT 'Cohort 1'"
                )
            except Exception:
                pass

        if not _column_exists(cur, "users", "active"):
            try:
                cur.execute(
                    "ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1"
                )
            except Exception:
                pass


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
            submitted_at TEXT
        )
        """)


        # ================= SUPPORT =================
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

        if not _column_exists(cur, "broadcasts", "subject"):
            try:
                cur.execute(
                    "ALTER TABLE broadcasts ADD COLUMN subject TEXT"
                )
            except Exception:
                pass


        # ================= CERTIFICATES =================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            issued_at TEXT,
            certificate_path TEXT
        )
        """)

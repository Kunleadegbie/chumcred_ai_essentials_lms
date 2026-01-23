
# services/db.py
# services/db.py
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

try:
    from filelock import FileLock
except Exception:
    FileLock = None


# -------------------------------------------------
# DB PATH (Railway-safe)
# -------------------------------------------------
DEFAULT_DB = "chumcred_lms.db"
DB_PATH = os.getenv("LMS_DB_PATH", DEFAULT_DB)
LOCK_PATH = f"{DB_PATH}.lock"

_DB_LOCK = FileLock(LOCK_PATH) if FileLock else None


def _ensure_dir():
    parent = os.path.dirname(DB_PATH)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def get_conn():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
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
    if _DB_LOCK:
        with _DB_LOCK:
            conn = get_conn()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    else:
        conn = get_conn()
        try:
            conn.execute("BEGIN IMMEDIATE;")
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

        # ---------------- USERS ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT,
            email TEXT,
            cohort TEXT DEFAULT 'Cohort 1',
            role TEXT DEFAULT 'student',
            password_hash BLOB,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """)

        # ---------------- PROGRESS ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            status TEXT DEFAULT 'locked',
            override_by_admin INTEGER DEFAULT 0,
            updated_at TEXT,
            UNIQUE(user_id, week),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        # ---------------- ASSIGNMENTS ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            file_path TEXT,
            submitted_at TEXT,
            status TEXT DEFAULT 'submitted',
            grade INTEGER,
            feedback TEXT,
            reviewed_at TEXT,
            UNIQUE(user_id, week),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        # ---------------- CERTIFICATES ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            issued_at TEXT,
            certificate_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        # ---------------- SUPPORT / HELP ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            admin_reply TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT,
            replied_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        # ---------------- BROADCASTS ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_by INTEGER,
            created_at TEXT,
            active INTEGER DEFAULT 1
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_reads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            broadcast_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            read_at TEXT,
            UNIQUE(broadcast_id, user_id)
        )
        """)

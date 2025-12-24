
# services/db.py
import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

import bcrypt

# Add to requirements.txt on Railway:
# filelock
try:
    from filelock import FileLock
except Exception:
    FileLock = None


DEFAULT_DB = "chumcred_lms.db"
DB_PATH = os.getenv("LMS_DB_PATH", DEFAULT_DB)

LOCK_PATH = os.getenv("LMS_DB_LOCK_PATH", f"{DB_PATH}.lock")
_DB_LOCK = FileLock(LOCK_PATH) if FileLock else None


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _safe_set_pragmas(conn: sqlite3.Connection) -> None:
    """
    Pragmas for better concurrency. WAL may fail on some FS; handle safely.
    """
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=30000;")  # 30s

    # Try WAL; if it fails, don't crash the app.
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        # Fallback for filesystems that don't support WAL well
        conn.execute("PRAGMA journal_mode=DELETE;")
        conn.execute("PRAGMA synchronous=FULL;")

    try:
        conn.execute("PRAGMA temp_store=MEMORY;")
    except Exception:
        pass


def get_conn() -> sqlite3.Connection:
    """
    Connection factory with Streamlit-safe SQLite settings.
    """
    _ensure_parent_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    _safe_set_pragmas(conn)
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
    """
    Serializes writes to prevent 'database is locked' on Streamlit/Railway.
    Use this for INSERT/UPDATE/DELETE.
    """
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
        # Works but less safe. Install filelock in production.
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


def _get_columns(cur: sqlite3.Cursor, table: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return [r["name"] for r in cur.fetchall()]


def _add_column_if_missing(cur: sqlite3.Cursor, table: str, col_def: str) -> None:
    col_name = col_def.split()[0].strip()
    if col_name not in _get_columns(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")


def _ensure_default_admin(cur: sqlite3.Cursor) -> None:
    admin_username = os.getenv("ADMIN_USERNAME", "admin").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123").strip()
    admin_email = os.getenv("ADMIN_EMAIL", "admin@chumcred.com").strip()
    admin_cohort = os.getenv("ADMIN_COHORT", "Staff").strip()
    force_reset = os.getenv("ADMIN_FORCE_RESET", "0").strip() == "1"

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cur.fetchone():
        return

    cur.execute("SELECT id FROM users WHERE username=? AND role='admin'", (admin_username,))
    existing = cur.fetchone()

    pw_hash = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt())
    now = datetime.utcnow().isoformat()

    if existing:
        if force_reset:
            cur.execute(
                "UPDATE users SET password_hash=?, email=?, cohort=?, active=1 WHERE id=?",
                (pw_hash, admin_email, admin_cohort, existing["id"]),
            )
        return

    cur.execute(
        """
        INSERT INTO users (username, email, cohort, role, password_hash, active, created_at)
        VALUES (?, ?, ?, 'admin', ?, 1, ?)
        """,
        (admin_username, admin_email, admin_cohort, pw_hash, now),
    )


def init_db() -> None:
    """
    Creates tables + safe migrations, plus indexes.
    Adds Help feature support_tickets table too.
    """
    with write_txn() as conn:
        cur = conn.cursor()

        # ---------------- USERS ----------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT,
                email TEXT,
                cohort TEXT DEFAULT 'Cohort 1',
                role TEXT NOT NULL DEFAULT 'student',
                password_hash BLOB,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT
            )
            """
        )
        _add_column_if_missing(cur, "users", "full_name TEXT")
        _add_column_if_missing(cur, "users", "email TEXT")
        _add_column_if_missing(cur, "users", "cohort TEXT DEFAULT 'Cohort 1'")
        _add_column_if_missing(cur, "users", "role TEXT NOT NULL DEFAULT 'student'")
        _add_column_if_missing(cur, "users", "password_hash BLOB")
        _add_column_if_missing(cur, "users", "active INTEGER NOT NULL DEFAULT 1")
        _add_column_if_missing(cur, "users", "created_at TEXT")

        # ---------------- PROGRESS ----------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                week INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'locked',
                override_by_admin INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT,
                UNIQUE(user_id, week),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        _add_column_if_missing(cur, "progress", "status TEXT NOT NULL DEFAULT 'locked'")
        _add_column_if_missing(cur, "progress", "override_by_admin INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(cur, "progress", "updated_at TEXT")

        # ---------------- ASSIGNMENTS ----------------
        cur.execute(
            """
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
            """
        )
        _add_column_if_missing(cur, "assignments", "file_path TEXT")
        _add_column_if_missing(cur, "assignments", "submitted_at TEXT")
        _add_column_if_missing(cur, "assignments", "status TEXT DEFAULT 'submitted'")
        _add_column_if_missing(cur, "assignments", "grade INTEGER")
        _add_column_if_missing(cur, "assignments", "feedback TEXT")
        _add_column_if_missing(cur, "assignments", "reviewed_at TEXT")

        # ---------------- CERTIFICATES ----------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                issued_at TEXT,
                certificate_path TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        _add_column_if_missing(cur, "certificates", "issued_at TEXT")
        _add_column_if_missing(cur, "certificates", "certificate_path TEXT")

        # ---------------- SUPPORT TICKETS (HELP FEATURE) ----------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                admin_reply TEXT,
                created_at TEXT,
                replied_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        _add_column_if_missing(cur, "support_tickets", "subject TEXT")
        _add_column_if_missing(cur, "support_tickets", "status TEXT NOT NULL DEFAULT 'open'")
        _add_column_if_missing(cur, "support_tickets", "admin_reply TEXT")
        _add_column_if_missing(cur, "support_tickets", "created_at TEXT")
        _add_column_if_missing(cur, "support_tickets", "replied_at TEXT")

        # ---------------- INDEXES (performance) ----------------
        cur.execute("CREATE INDEX IF NOT EXISTS idx_progress_user_week ON progress(user_id, week)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_assign_user_week ON assignments(user_id, week)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user_status ON support_tickets(user_id, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status)")

        # Ensure default admin exists
        _ensure_default_admin(cur)

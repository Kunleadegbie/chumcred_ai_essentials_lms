
# services/db.py
import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

import bcrypt

# IMPORTANT for production locking (Railway / Linux)
# Add to requirements.txt: filelock
try:
    from filelock import FileLock
except Exception:
    FileLock = None  # app still runs, but write locking is weaker


# -----------------------------------------
# DB PATH (Railway-friendly)
# -----------------------------------------
# Set this in Railway Variables for persistence:
# LMS_DB_PATH=/app/data/chumcred_lms.db
DEFAULT_DB = "chumcred_lms.db"
DB_PATH = os.getenv("LMS_DB_PATH", DEFAULT_DB)

# Lock file should live beside the DB file (same volume)
LOCK_PATH = os.getenv("LMS_DB_LOCK_PATH", f"{DB_PATH}.lock")
_DB_LOCK = FileLock(LOCK_PATH) if FileLock else None


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    """
    Connection factory with Streamlit-safe SQLite pragmas.
    WAL + busy_timeout reduces lock errors, plus write_txn serializes writes.
    """
    _ensure_parent_dir(DB_PATH)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA busy_timeout=30000;")  # 30s

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
    Use for ALL writes (INSERT/UPDATE/DELETE).
    Serializes writes to prevent 'database is locked' in Streamlit.
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
    rows = cur.fetchall()
    # sqlite3.Row: name at ["name"], tuple: name at [1]
    return [(r["name"] if isinstance(r, sqlite3.Row) else r[1]) for r in rows]


def _add_column_if_missing(cur: sqlite3.Cursor, table: str, col_def: str) -> None:
    col_name = col_def.split()[0].strip()
    cols = _get_columns(cur, table)
    if col_name not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")


def _ensure_default_admin(cur: sqlite3.Cursor) -> None:
    """
    Ensures at least one admin exists.
    If ADMIN_FORCE_RESET=1, resets admin password to ADMIN_PASSWORD.
    """
    admin_username = os.getenv("ADMIN_USERNAME", "admin").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123").strip()
    admin_email = os.getenv("ADMIN_EMAIL", "admin@chumcred.com").strip()
    admin_cohort = os.getenv("ADMIN_COHORT", "Staff").strip()
    force_reset = os.getenv("ADMIN_FORCE_RESET", "0").strip() == "1"

    cur.execute("SELECT id, password_hash FROM users WHERE username=? AND role='admin'", (admin_username,))
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
    Creates tables + runs safe migrations (so old Railway DBs won't crash).
    Also ensures a default admin exists.
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
                original_filename TEXT,
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
        _add_column_if_missing(cur, "assignments", "original_filename TEXT")
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
        # IMPORTANT: keep schema consistent with Help UI: user_id + username
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
                replied_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        _add_column_if_missing(cur, "support_tickets", "subject TEXT")
        _add_column_if_missing(cur, "support_tickets", "status TEXT NOT NULL DEFAULT 'open'")
        _add_column_if_missing(cur, "support_tickets", "admin_reply TEXT")
        _add_column_if_missing(cur, "support_tickets", "created_at TEXT")
        _add_column_if_missing(cur, "support_tickets", "replied_at TEXT")
        _add_column_if_missing(cur, "support_tickets", "replied_by INTEGER")

        # ---------------- INDEXES (performance) ----------------
        cur.execute("CREATE INDEX IF NOT EXISTS idx_progress_user_week ON progress(user_id, week)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_assign_user_week ON assignments(user_id, week)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user_status ON support_tickets(user_id, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status)")

        # Ensure default admin exists
        _ensure_default_admin(cur)

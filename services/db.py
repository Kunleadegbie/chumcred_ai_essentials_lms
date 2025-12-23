
# services/db.py
import os
import sqlite3
from datetime import datetime

# Optional, but strongly recommended for password hashing
import bcrypt

# -----------------------------------------
# DB PATH (Railway-friendly)
# -----------------------------------------
# Set this in Railway Variables for persistence:
# LMS_DB_PATH=/app/data/chumcred_lms.db
DEFAULT_DB = "chumcred_lms.db"
DB_PATH = os.getenv("LMS_DB_PATH", DEFAULT_DB)


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_parent_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _get_columns(cur: sqlite3.Cursor, table: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({table})")
    rows = cur.fetchall()
    # sqlite Row: name is at key "name", fallback index 1
    return [(r["name"] if isinstance(r, sqlite3.Row) else r[1]) for r in rows]


def _add_column_if_missing(cur: sqlite3.Cursor, table: str, col_def: str) -> None:
    """
    col_def example: "cohort TEXT DEFAULT 'Cohort 1'"
    """
    col_name = col_def.split()[0].strip()
    cols = _get_columns(cur, table)
    if col_name not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")


def _ensure_default_admin(cur: sqlite3.Cursor) -> None:
    """
    Ensures at least one admin exists.
    Uses env vars if provided; otherwise defaults to admin/admin123.
    """
    cur.execute("SELECT COUNT(1) AS c FROM users WHERE role = 'admin'")
    count = cur.fetchone()["c"]
    if count and int(count) > 0:
        return

    admin_username = os.getenv("ADMIN_USERNAME", "admin").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123").strip()
    admin_email = os.getenv("ADMIN_EMAIL", "admin@chumcred.com").strip()
    admin_cohort = os.getenv("ADMIN_COHORT", "Staff").strip()

    pw_hash = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt())
    now = datetime.utcnow().isoformat()

    cur.execute(
        """
        INSERT OR IGNORE INTO users (username, email, cohort, role, password_hash, active, created_at)
        VALUES (?, ?, ?, 'admin', ?, 1, ?)
        """,
        (admin_username, admin_email, admin_cohort, pw_hash, now),
    )


def init_db() -> None:
    """
    Creates tables + runs safe migrations (so old Railway DBs won't crash).
    Also ensures a default admin exists.
    """
    conn = get_conn()
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

    # Migrations for older DBs
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

    # Ensure default admin exists (so you can always log in)
    _ensure_default_admin(cur)

    conn.commit()
    conn.close()

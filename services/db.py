# services/db.py
import os
import sqlite3
from datetime import datetime

try:
    import bcrypt
except Exception:
    bcrypt = None


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Railway tip: set LMS_DB_PATH=/app/data/chumcred_lms.db
DB_PATH = os.environ.get("LMS_DB_PATH") or os.path.join(PROJECT_ROOT, "chumcred_lms.db")


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_parent_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(cur: sqlite3.Cursor, table: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return [r["name"] if isinstance(r, sqlite3.Row) else r[1] for r in cur.fetchall()]


def _add_column_if_missing(cur: sqlite3.Cursor, table: str, col_def: str) -> None:
    """
    col_def example: "cohort TEXT DEFAULT 'Cohort 1'"
    """
    col_name = col_def.split()[0].strip()
    cols = _table_columns(cur, table)
    if col_name not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")


def init_db() -> None:
    """
    Creates tables if missing and runs safe migrations for older DBs.
    This prevents Railway crashes like: sqlite3.OperationalError: no such column: cohort
    """
    conn = get_conn()
    cur = conn.cursor()

    # -----------------------------
    # USERS (newest schema)
    # -----------------------------
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

    # Migrations for older users table
    # (If you previously had: password TEXT NOT NULL, role TEXT NOT NULL, etc.)
    _add_column_if_missing(cur, "users", "full_name TEXT")
    _add_column_if_missing(cur, "users", "email TEXT")
    _add_column_if_missing(cur, "users", "cohort TEXT DEFAULT 'Cohort 1'")
    _add_column_if_missing(cur, "users", "password_hash BLOB")
    _add_column_if_missing(cur, "users", "active INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(cur, "users", "created_at TEXT")

    # If older DB had plaintext `password` column, try to migrate it into password_hash
    cols = _table_columns(cur, "users")
    if "password" in cols and bcrypt is not None:
        # Hash any users missing password_hash
        cur.execute("SELECT id, password, password_hash FROM users")
        rows = cur.fetchall()
        for r in rows:
            uid = r["id"]
            pw = r["password"]
            ph = r["password_hash"]
            if pw and (ph is None or ph == b"" or ph == ""):
                hashed = bcrypt.hashpw(str(pw).encode("utf-8"), bcrypt.gensalt())
                cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, uid))

    # Normalize bcrypt hashes stored as TEXT into bytes (prevents bcrypt.checkpw crash)
    if bcrypt is not None:
        cur.execute("SELECT id, password_hash FROM users WHERE password_hash IS NOT NULL")
        rows = cur.fetchall()
        for r in rows:
            uid = r["id"]
            ph = r["password_hash"]
            if isinstance(ph, str):
                cur.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (ph.encode("utf-8"), uid),
                )

    # Ensure created_at exists for existing rows
    now = datetime.utcnow().isoformat()
    cur.execute("UPDATE users SET created_at = COALESCE(created_at, ?) ", (now,))

    # -----------------------------
    # PROGRESS
    # -----------------------------
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
    cur.execute("UPDATE progress SET updated_at = COALESCE(updated_at, ?) ", (now,))

    # -----------------------------
    # ASSIGNMENTS
    # -----------------------------
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

    # -----------------------------
    # CERTIFICATES
    # -----------------------------
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

    conn.commit()
    conn.close()

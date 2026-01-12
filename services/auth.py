

# services/auth.py
import sqlite3
from typing import Optional, Any

import streamlit as st
import bcrypt

from services.db import read_conn, write_txn


# -----------------------------
# Password helpers (bcrypt) new
# -----------------------------
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def _to_bytes(value: Any) -> Optional[bytes]:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, str):
        # (defensive) if it ever ends up stored as text
        return value.encode("utf-8")
    return None


def verify_password(password: str, hashed: Any) -> bool:
    hb = _to_bytes(hashed)
    if not hb:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hb)
    except Exception:
        return False


# -----------------------------
# User CRUD
# -----------------------------
def create_user(
    username: str,
    password: str,
    role: str = "student",
    cohort: str = "Cohort 1",
    email: str | None = None,
    full_name: str | None = None,
) -> int:
    """
    Creates a user using write_txn() to prevent Railway/SQLite locking.
    Returns new user_id.
    """
    uname = (username or "").strip()
    if not uname:
        raise ValueError("Username is required.")
    if not password:
        raise ValueError("Password is required.")

    pw_hash = hash_password(password)

    try:
        with write_txn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO users (username, full_name, email, cohort, role, password_hash, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))
                """,
                (uname, full_name, email, (cohort or "Cohort 1").strip(), (role or "student").strip(), pw_hash),
            )
            return int(cur.lastrowid)
    except sqlite3.IntegrityError as e:
        # Most common: UNIQUE constraint failed: users.username
        raise ValueError(f"User already exists or invalid data: {e}") from e


def get_all_students():
    """
    Used by Admin -> All Students page.
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, username, cohort, email, full_name, active, created_at
            FROM users
            WHERE role='student'
            ORDER BY cohort, username
            """
        )
        return [dict(r) for r in cur.fetchall()]


def get_all_cohorts():
    """
    Used by Admin filters.
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT COALESCE(cohort,'Cohort 1') AS cohort
            FROM users
            WHERE role='student'
            ORDER BY cohort
            """
        )
        return [r["cohort"] for r in cur.fetchall()]


def reset_user_password(username: str, new_password: str) -> None:
    """
    Admin utility: resets a user's password.
    NOTE: you cannot "fetch" existing passwords from hashes; only reset.
    """
    uname = (username or "").strip()
    if not uname:
        raise ValueError("Username is required.")
    if not new_password:
        raise ValueError("New password is required.")

    new_hash = hash_password(new_password)

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, uname))
        if cur.rowcount == 0:
            raise ValueError("User not found.")


# -----------------------------
# Streamlit login/logout
# -----------------------------
def login_user():
    """
    Streamlit login form. Returns user dict if authenticated else None.
    """
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="e.g. admin")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Login")

    if not submitted:
        return None

    if not username or not password:
        st.error("Please enter username and password.")
        return None

    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, username, role, COALESCE(cohort,'Cohort 1') AS cohort, password_hash, active
            FROM users
            WHERE username = ?
            """,
            (username.strip(),),
        )
        row = cur.fetchone()

    if not row:
        st.error("Invalid username or password.")
        return None

    if int(row["active"]) != 1:
        st.error("Your account is disabled. Please contact admin.")
        return None

    if not verify_password(password, row["password_hash"]):
        st.error("Invalid username or password.")
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "cohort": row["cohort"],
    }


def logout():
    st.session_state.user = None
    st.rerun()

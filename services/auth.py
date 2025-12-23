
# services/auth.py
from __future__ import annotations

import streamlit as st
import hashlib
from typing import Optional, Dict, List

from services.db import get_conn
from services.progress import seed_progress_for_user


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    return hash_password(password) == stored_hash


def _users_table_columns() -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in cur.fetchall()]
    conn.close()
    return cols


def create_user(username: str, password: str, role: str = "student", cohort: str = "Cohort 1") -> int:
    username = username.strip()
    cohort = (cohort or "Cohort 1").strip()

    cols = _users_table_columns()
    use_password_hash = "password_hash" in cols

    conn = get_conn()
    cur = conn.cursor()

    pw_hash = hash_password(password)

    if use_password_hash:
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, cohort)
            VALUES (?, ?, ?, ?)
            """,
            (username, pw_hash, role, cohort),
        )
    else:
        # fallback older schema
        cur.execute(
            """
            INSERT INTO users (username, password, role, cohort)
            VALUES (?, ?, ?, ?)
            """,
            (username, pw_hash, role, cohort),
        )

    conn.commit()
    user_id = cur.lastrowid
    conn.close()

    if role == "student":
        seed_progress_for_user(user_id)

    return user_id


def login_user() -> Optional[Dict]:
    if "user" in st.session_state and st.session_state["user"]:
        return st.session_state["user"]

    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        cols = _users_table_columns()
        has_password_hash = "password_hash" in cols

        conn = get_conn()
        cur = conn.cursor()

        if has_password_hash:
            cur.execute(
                """
                SELECT id, username, password_hash, role, COALESCE(cohort, 'Cohort 1')
                FROM users
                WHERE username = ?
                """,
                (username.strip(),),
            )
        else:
            cur.execute(
                """
                SELECT id, username, password, role, COALESCE(cohort, 'Cohort 1')
                FROM users
                WHERE username = ?
                """,
                (username.strip(),),
            )

        row = cur.fetchone()
        conn.close()

        if not row:
            st.error("Invalid username or password.")
            return None

        user_id, uname, stored_hash, role, cohort = row

        # If old DB stored plaintext in password, this will fail.
        # If it fails, we prompt admin to recreate user properly.
        if not verify_password(password, stored_hash):
            st.error("Invalid username or password.")
            return None

        user = {"id": user_id, "username": uname, "role": role, "cohort": cohort}
        st.session_state["user"] = user
        st.success("Login successful.")
        st.rerun()

    return None


def get_all_students() -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, role, COALESCE(cohort, 'Cohort 1')
        FROM users
        WHERE role = 'student'
        ORDER BY username
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "username": r[1], "role": r[2], "cohort": r[3]} for r in rows]


def get_all_cohorts() -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT COALESCE(cohort, 'Cohort 1') AS cohort
        FROM users
        WHERE role = 'student'
        ORDER BY cohort
        """
    )
    rows = cur.fetchall()
    conn.close()
    cohorts = [r[0] for r in rows] if rows else []
    return cohorts if cohorts else ["Cohort 1"]


def set_student_cohort(username: str, cohort: str) -> bool:
    cohort = (cohort or "Cohort 1").strip()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users
        SET cohort = ?
        WHERE username = ? AND role = 'student'
        """,
        (cohort, username),
    )
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated

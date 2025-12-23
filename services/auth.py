

# services/auth.py
import streamlit as st
import bcrypt
from services.db import get_conn


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def _to_bytes(value) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, str):
        return value.encode("utf-8")
    return None


def verify_password(password: str, hashed) -> bool:
    hb = _to_bytes(hashed)
    if not hb:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hb)
    except Exception:
        return False


def create_user(username: str, password: str, role: str = "student", cohort: str = "Cohort 1", email: str | None = None, full_name: str | None = None):
    conn = get_conn()
    cur = conn.cursor()

    pw_hash = hash_password(password)

    cur.execute(
        """
        INSERT INTO users (username, full_name, email, cohort, role, password_hash, active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))
        """,
        (username.strip(), full_name, email, cohort, role, pw_hash),
    )
    conn.commit()
    conn.close()


def get_all_students():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, cohort, email, full_name, active, created_at
        FROM users
        WHERE role='student'
        ORDER BY cohort, username
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_all_cohorts():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT COALESCE(cohort,'Cohort 1') AS cohort
        FROM users
        WHERE role='student'
        ORDER BY cohort
        """
    )
    cohorts = [r["cohort"] for r in cur.fetchall()]
    conn.close()
    return cohorts


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

    conn = get_conn()
    cur = conn.cursor()

    # Fetch the user
    cur.execute(
        """
        SELECT id, username, role, cohort, password_hash, active
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

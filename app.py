# app.py
import os
import streamlit as st

# MUST be the first Streamlit command in the file
st.set_page_config(
    page_title="Chumcred Academy LMS",
    page_icon="🎓",
    layout="wide"
)

# Imports AFTER set_page_config (this is correct)
from services.db import init_db  # noqa: E402
from services.auth import login_user  # noqa: E402
from ui.admin import admin_router  # noqa: E402
from ui.student import student_router  # noqa: E402


def _logo_path():
    # Try common locations safely
    candidates = [
        os.path.join("assets", "logo.png"),
        "logo.png",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _env_health_checks():
    """
    Non-blocking production checks.
    Does NOT affect admin login.
    Just helps you diagnose Railway issues fast.
    """
    # On Railway, you SHOULD set LMS_DB_PATH to a persistent volume path e.g. /app/data/chumcred_lms.db
    db_path = os.getenv("LMS_DB_PATH", "").strip()
    if db_path:
        # If DB folder doesn't exist, db.py should create it, but this hint helps
        parent = os.path.dirname(db_path)
        if parent and not os.path.exists(parent):
            st.sidebar.warning(
                f"DB folder not found: {parent}\n"
                "If you're on Railway, ensure you mounted a Volume to /app/data "
                "and set LMS_DB_PATH=/app/data/chumcred_lms.db"
            )
    


# 1) Ensure DB + migrations + default admin are ready BEFORE login
init_db()

# Session bootstrap
if "user" not in st.session_state:
    st.session_state.user = None

# Sidebar branding
with st.sidebar:
    lp = _logo_path()
    if lp:
        st.image(lp, width=170)
    st.markdown("## Chumcred Academy LMS")
    _env_health_checks()

# 2) Login then route
if st.session_state.user is None:
    st.title("🔐 Login")
    st.caption("Use your provided credentials to continue.")

    user = login_user()

    if user:
        st.session_state.user = user
        st.rerun()
else:
    user = st.session_state.user

    # ✅ Safe guard: if user record changed/disabled, force logout cleanly
    if not user.get("role") or not user.get("username"):
        st.session_state.user = None
        st.rerun()

    if user.get("role") == "admin":
        admin_router(user)
    else:
        student_router(user)

import os
import streamlit as st

from services.db import ensure_exam_tables

ensure_exam_tables()

# MUST be the first Streamlit command
st.set_page_config(
    page_title="Chumcred Academy LMS",
    page_icon="🎓",
    layout="wide"
)

# Imports AFTER set_page_config
from services.db import init_db
from services.auth import login_user
from ui.admin import admin_router
from ui.student import student_router


def _logo_path():
    """Locate logo safely"""
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
    Non-blocking production checks
    Useful for Railway deployment diagnostics
    """
    db_path = os.getenv("LMS_DB_PATH", "").strip()

    if db_path:
        parent = os.path.dirname(db_path)

        if parent and not os.path.exists(parent):
            st.sidebar.warning(
                f"Database folder not found: {parent}\n\n"
                "If deploying on Railway, mount a Volume to /app/data "
                "and set LMS_DB_PATH=/app/data/chumcred_lms.db"
            )


# ----------------------------------------------------
# 1. INITIALIZE DATABASE
# ----------------------------------------------------
init_db()


# ----------------------------------------------------
# 2. SESSION INITIALIZATION
# ----------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None


# ----------------------------------------------------
# 3. SIDEBAR BRANDING
# ----------------------------------------------------
with st.sidebar:
    logo = _logo_path()
    if logo:
        st.image(logo, width=170)

    st.markdown("## Chumcred Academy LMS")

    _env_health_checks()


# ----------------------------------------------------
# 4. LOGIN FLOW
# ----------------------------------------------------
if st.session_state.user is None:

    st.title("🔐 Login")
    st.caption("Enter your LMS credentials to continue.")

    user = login_user()

    if user:
        st.session_state.user = user
        st.rerun()

    st.stop()


# ----------------------------------------------------
# 5. AFTER LOGIN → ROUTE USER
# ----------------------------------------------------
user = st.session_state.user

# Safety check if account was disabled or corrupted
if not user.get("role") or not user.get("username"):
    st.session_state.user = None
    st.rerun()


# ----------------------------------------------------
# 6. ROLE-BASED ROUTING
# ----------------------------------------------------
if user.get("role") == "admin":

    # Admin sidebar + pages handled inside admin_router
    admin_router(user)

else:

    # Student sidebar + pages handled inside student_router
    student_router(user)
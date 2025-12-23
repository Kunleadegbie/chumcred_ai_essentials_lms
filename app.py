# app.py
import os
import streamlit as st

# ✅ MUST be the first Streamlit command
st.set_page_config(
    page_title="Chumcred Academy LMS",
    page_icon="🎓",
    layout="wide",
)

from services.db import init_db
from services.auth import login_user
from ui.admin import admin_router
from ui.student import student_router


def _find_logo_path() -> str | None:
    """
    Tries common logo locations without crashing Streamlit.
    """
    candidates = [
        os.path.join("assets", "logo.png"),
        "logo.png",
        os.path.join("assets", "logo.jpg"),
        "logo.jpg",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


# Initialize DB (safe migrations included)
init_db()

# Session user persistence
if "user" not in st.session_state:
    st.session_state.user = None

# Sidebar branding
with st.sidebar:
    logo_path = _find_logo_path()
    if logo_path:
        st.image(logo_path, width=180)
    st.markdown("## Chumcred Academy LMS")

# Login / Route
if st.session_state.user is None:
    st.title("🔐 Login")
    user = login_user()
    if user:
        st.session_state.user = user
        st.rerun()
    else:
        st.info("Please log in to continue.")
else:
    user = st.session_state.user

    # Route based on role
    if user.get("role") == "admin":
        admin_router(user)
    else:
        student_router(user)

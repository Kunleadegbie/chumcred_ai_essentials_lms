# app.py
import os
import streamlit as st

# MUST be the first Streamlit command in the file
st.set_page_config(
    page_title="Chumcred Academy LMS",
    page_icon="🎓",
    layout="wide"
)

from services.db import init_db
from services.auth import login_user
from ui.admin import admin_router
from ui.student import student_router


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
    if user.get("role") == "admin":
        admin_router(user)
    else:
        student_router(user)

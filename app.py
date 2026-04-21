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
from services.db import init_db, read_conn
from services.auth import login_user
from ui.admin import admin_router
from ui.student import student_router
from ui.landing import render_landing_page


def _env_health_checks():
    """
    Non-blocking production checks
    Useful for Railway deployment diagnostics
    """
    db_path = os.getenv("LMS_DB_PATH", "").strip()

    if db_path:
        parent = os.path.dirname(db_path)
        if parent and not os.path.exists(parent):
            st.warning(
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

# Optional environment checks (now shown in main page, not sidebar)
_env_health_checks()

# ----------------------------------------------------
# 3. LOGIN FLOW (shows landing + login when not logged in)
# ----------------------------------------------------
if st.session_state.user is None:
    # ✅ ONLY ON LANDING/LOGIN: hide sidebar + make full-width
    st.markdown(
        """
        <style>
          /* Hide Streamlit sidebar + nav completely (landing only) */
          [data-testid="stSidebar"] { display: none !important; }
          [data-testid="stSidebarNav"] { display: none !important; }

          /* Make main content full-width */
          .block-container {
            max-width: 100% !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
            padding-top: 1.5rem !important;
          }

          /* Optional: hide Streamlit header (hamburger/menu area) on landing only */
          header { visibility: hidden; height: 0; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Landing page first
    render_landing_page()

    st.markdown("---")
    st.markdown("## 🔐 Login to Continue")
    st.caption("Enter your LMS credentials to continue.")

    user = login_user()

    if user:
        st.session_state.user = user
        st.rerun()

    st.stop()

# ----------------------------------------------------
# 4. AFTER LOGIN → ROUTE USER
# ----------------------------------------------------
user = st.session_state.user

# ✅ AFTER LOGIN: restore sidebar + restore header (undo landing CSS)
st.markdown(
    """
    <style>
      /* Restore sidebar after login */
      [data-testid="stSidebar"] { display: block !important; }
      [data-testid="stSidebarNav"] { display: block !important; }

      /* Restore header after login */
      header { visibility: visible; height: auto; }
    </style>
    """,
    unsafe_allow_html=True
)

# Safety check if account was disabled or corrupted
if not user.get("role") or not user.get("username"):
    st.session_state.user = None
    st.rerun()

# ----------------------------------------------------
# 5. BLOCK / UNBLOCK ENFORCEMENT (kept as-is)
# ----------------------------------------------------
try:
    with read_conn() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]

        # Option A: is_blocked column
        if "is_blocked" in cols:
            row = conn.execute(
                "SELECT is_blocked, blocked_reason FROM users WHERE id = ?",
                (user.get("id"),)
            ).fetchone()

            if row and int(row[0] or 0) == 1:
                st.error("🚫 Your account has been blocked. Please contact the administrator.")
                if len(row) > 1 and row[1]:
                    st.caption(f"Reason: {row[1]}")
                st.stop()

        # Option B: status column
        elif "status" in cols:
            row = conn.execute(
                "SELECT status FROM users WHERE id = ?",
                (user.get("id"),)
            ).fetchone()

            if row and str(row[0] or "").strip().lower() == "blocked":
                st.error("🚫 Your account has been blocked. Please contact the administrator.")
                st.stop()

except Exception:
    pass

# ----------------------------------------------------
# 6. ROLE-BASED ROUTING
# ----------------------------------------------------
if user.get("role") == "admin":
    admin_router(user)
else:
    student_router(user)
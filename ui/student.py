
# ui/student.py

import os
import streamlit as st

from services.progress import (
    get_progress,
    mark_week_completed,
)
from services.assignments import save_assignment, has_assignment
from ui.help import help_router

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


# --------------------------------------------------
# Orientation (Week 0)
# --------------------------------------------------
def render_week_0(user):
    st.header("📘 Orientation — Mandatory")

    md_path = os.path.join(CONTENT_DIR, "week0.md")
    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)
    else:
        st.warning("Orientation content missing.")

    st.divider()

    if st.button("✅ Mark Orientation as Completed"):
        mark_week_completed(user["id"], 0)
        st.success("Orientation completed.")
        st.rerun()


# --------------------------------------------------
# Student Dashboard
# --------------------------------------------------
def student_router(user):
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user['username']}")

    progress = get_progress(user["id"])

    # 🚨 Enforce Orientation first
    if progress.get(0) != "completed":
        render_week_0(user)
        return

    st.divider()

    # --------------------------------------------------
    # Week Selection (ALX-style cards)
    # --------------------------------------------------
    st.subheader("📘 Course Progress")

    cols = st.columns(3)
    selected_week = None

    for week in range(1, TOTAL_WEEKS + 1):
        status = progress.get(week, "locked")
        col = cols[(week - 1) % 3]

        with col:
            if status == "unlocked":
                if st.button(f"Week {week} ✅", key=f"week_{week}"):
                    selected_week = week
            elif status == "completed":
                if st.button(f"Week {week} ✔️", key=f"week_{week}"):
                    selected_week = week
            else:
                st.button(f"Week {week} 🔒", disabled=True)

    st.divider()

    # --------------------------------------------------
    # Week Content
    # --------------------------------------------------
    if selected_week:
        st.header(f"📘 Week {selected_week}")

        md_path = os.path.join(CONTENT_DIR, f"week{selected_week}.md")
        if not os.path.exists(md_path):
            st.error("Week content not found.")
            return

        with open(md_path, "r", encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)

        st.divider()

        # --------------------------------------------------
        # Assignment Submission
        # --------------------------------------------------
        st.subheader("📤 Assignment Submission")

        if has_assignment(user["id"], selected_week):
            st.success("✅ Assignment already submitted.")
        else:
            uploaded_file = st.file_uploader(
                "Upload assignment (PDF only)",
                type=["pdf"],
                key=f"upload_{selected_week}",
            )

            if uploaded_file and st.button("Submit Assignment"):
                save_assignment(user["id"], selected_week, uploaded_file)
                mark_week_completed(user["id"], selected_week)
                st.success("🎉 Assignment submitted successfully.")
                st.rerun()

    # --------------------------------------------------
    # Sidebar
    # --------------------------------------------------
    with st.sidebar:
        logo_path = None
        for p in ("assets/logo.png", "logo.png"):
            if os.path.exists(p):
                logo_path = p
                break

        if logo_path:
            st.image(logo_path, width=160)

        st.markdown("### 👩‍🎓 Student Menu")
        st.markdown(f"**User:** {user['username']}")

        completed = sum(1 for s in progress.values() if s == "completed")
        st.progress(completed / (TOTAL_WEEKS + 1))

        st.divider()
        help_router(user, role="student")

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

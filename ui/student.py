

# --------------------------------------------------
# ui/student.py
# --------------------------------------------------
# ui/student.py
import os
import streamlit as st
from datetime import datetime

from services.progress import get_progress, mark_week_completed
from services.assignments import (
    save_assignment,
    has_assignment,
    list_student_assignments
)
from services.broadcasts import (
    get_active_broadcasts,
    has_read,
    mark_as_read
)

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


def student_router(user):
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user['username']}")

    # ---------------- BROADCAST POPUP ----------------
    broadcasts = get_active_broadcasts()
    for b in broadcasts:
        if not has_read(b["id"], user["id"]):
            with st.modal("📢 Announcement"):
                st.subheader(b["title"])
                st.write(b["message"])
                if st.button("Got it"):
                    mark_as_read(b["id"], user["id"])
                    st.rerun()
            st.stop()

    progress = get_progress(user["id"])

    # ---------------- ORIENTATION (WEEK 0) ----------------
    if progress.get(0) != "completed":
        st.warning("🚨 Orientation must be completed before accessing the course.")

        md = os.path.join(CONTENT_DIR, "week0.md")
        if os.path.exists(md):
            with open(md, encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)

        if st.button("✅ Mark Orientation Completed"):
            mark_week_completed(user["id"], 0)
            st.success("Orientation completed.")
            st.rerun()

        return

    # ---------------- WEEK CARDS ----------------
    st.subheader("📘 Course Progress")
    cols = st.columns(3)
    selected_week = None

    for week in range(1, TOTAL_WEEKS + 1):
        status = progress.get(week, "locked")
        col = cols[(week - 1) % 3]

        with col:
            label = f"Week {week}"
            if status == "locked":
                st.button(f"{label} 🔒", disabled=True)
            else:
                if st.button(f"{label} ✅" if status == "completed" else label):
                    selected_week = week

    # ---------------- WEEK CONTENT ----------------
    if selected_week:
        st.header(f"📘 Week {selected_week}")
        md = os.path.join(CONTENT_DIR, f"week{selected_week}.md")

        if not os.path.exists(md):
            st.error("Week content not found.")
            return

        with open(md, encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)

        st.divider()

        # ---------------- ASSIGNMENT ----------------
        st.subheader("📤 Assignment Submission")

        if has_assignment(user["id"], selected_week):
            st.success("Assignment already submitted.")
        else:
            uploaded = st.file_uploader("Upload PDF", type=["pdf"])
            if uploaded and st.button("Submit Assignment"):
                save_assignment(user["id"], selected_week, uploaded)
                st.success("Assignment submitted.")
                st.rerun()

    # ---------------- GRADES / TRANSCRIPT ----------------
    st.divider()
    st.subheader("📊 Your Grades")

    rows = list_student_assignments(user["id"])
    if rows:
        st.dataframe(rows)
    else:
        st.info("No graded assignments yet.")

    # ---------------- SIDEBAR ----------------
    

        completed = sum(1 for s in progress.values() if s == "completed")
        st.progress(completed / TOTAL_WEEKS)

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

with st.sidebar:
    st.markdown("### 👩‍🎓 Student Menu")

    if st.button("🏠 Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    if st.session_state.get("page") == "help":
        from ui.help import help_router
        help_router(user, role="student")
        return


    if st.button("🆘 Help & Support"):
        st.session_state.page = "help"
        st.rerun()

    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()


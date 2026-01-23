

# --------------------------------------------------
# ui/student.py
# --------------------------------------------------
# ui/student.py

import os
import streamlit as st

from services.progress import get_progress, mark_week_completed
from services.assignments import (
    save_assignment,
    has_assignment,
    list_student_assignments,
)
from services.broadcasts import (
    get_active_broadcasts,
    has_read,
    mark_as_read,
)

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


def student_router(user):
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user['username']}")

    # ---------------- SIDEBAR ----------------
    with st.sidebar:
        st.markdown("### 👩‍🎓 Student Menu")

        if st.button("🏠 Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()

        if st.button("🆘 Help & Support"):
            st.session_state.page = "help"
            st.rerun()

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    # ---------------- HELP ROUTING ----------------
    if st.session_state.get("page") == "help":
        from ui.help import help_router
        help_router(user, role="student")
        return

    # ---------------- BROADCAST POPUPS ----------------
    for b in get_active_broadcasts():
        if not has_read(b["id"], user["id"]):
            with st.modal("📢 Announcement"):
                st.subheader(b["title"])
                st.write(b["message"])
                if st.button("Got it"):
                    mark_as_read(b["id"], user["id"])
                    st.rerun()
            st.stop()

    progress = get_progress(user["id"])

    # ===============================
    # WEEK 0 — ORIENTATION (MANDATORY)
    # ===============================
    if progress.get(0) != "completed":
        st.warning("🚨 You must complete Orientation before accessing Week 1.")

        md_path = os.path.join(CONTENT_DIR, "week0.md")
        if os.path.exists(md_path):
            with open(md_path, encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.error("Orientation content not found.")

        if st.button("✅ Mark Orientation Completed"):
            mark_week_completed(user["id"], 0)
            st.success("Orientation completed successfully.")
            st.rerun()

        return  # 🔒 HARD STOP

    # ===============================
    # WEEK CARDS
    # ===============================
    st.subheader("📘 Course Progress")

    cols = st.columns(3)
    selected_week = None

    for week in range(1, TOTAL_WEEKS + 1):
        status = progress.get(week, "locked")
        col = cols[(week - 1) % 3]

        with col:
            if status == "locked":
                st.button(f"Week {week} 🔒", disabled=True)
            else:
                if st.button(f"Week {week} ✔️" if status == "completed" else f"Week {week}"):
                    selected_week = week

    # ===============================
    # WEEK CONTENT + ASSIGNMENT
    # ===============================
    if selected_week:
        st.header(f"📘 Week {selected_week}")

        md = os.path.join(CONTENT_DIR, f"week{selected_week}.md")
        if not os.path.exists(md):
            st.error("Week content not found.")
            return

        with open(md, encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)

        st.divider()
        st.subheader("📤 Assignment Submission")

        if has_assignment(user["id"], selected_week):
            st.success("Assignment already submitted.")
        else:
            uploaded = st.file_uploader("Upload PDF", type=["pdf"])
            if uploaded and st.button("Submit Assignment"):
                save_assignment(user["id"], selected_week, uploaded)
                st.success("Assignment submitted successfully.")
                st.rerun()

    # ===============================
    # GRADES
    # ===============================
    st.divider()
    st.subheader("📊 Your Grades")

    rows = list_student_assignments(user["id"])
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No graded assignments yet.")

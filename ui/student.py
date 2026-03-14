import os
import streamlit as st

from services.progress import (
    get_progress,
    mark_week_completed,
    is_orientation_completed,
    mark_orientation_completed,
)

from services.assignments import (
    save_assignment,
    has_assignment,
    get_week_grade,
    get_student_grade_summary,
    can_issue_certificate,
)

from services.certificates import has_certificate, issue_certificate

from services.db import read_conn

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


def student_router(user):

    st.title("🎓 AI Essentials — Student Dashboard")

    user_id = user["id"]

    progress = get_progress(user_id)

    # =================================================
    # COURSE PROGRESS
    # =================================================

    st.subheader("📘 Course Progress")

    cols = st.columns(3)

    for week in range(1, TOTAL_WEEKS + 1):

        status = progress.get(week, "locked")

        label = f"Week {week}"

        if status == "completed":
            label += " ✔️"

        elif status == "unlocked":
            label += " 🔓"

        else:
            label += " 🔒"

        with cols[(week-1)%3]:

            if status != "locked":

                if st.button(label):

                    st.session_state["selected_week"]=week

            else:

                st.button(label,disabled=True)

    # =================================================
    # FINAL EXAM
    # =================================================

    st.divider()

    st.subheader("📝 Final Exam")

    with read_conn() as conn:

        row = conn.execute(
            """
            SELECT exam_unlocked,exam_reviewed
            FROM student_exam_status
            WHERE user_id=?
            """,
            (user_id,),
        ).fetchone()

    if not row or not row["exam_unlocked"]:

        st.warning("Final exam locked by admin.")

    else:

        if row["exam_reviewed"]:

            st.error("Exam locked after review.")

        else:

            if st.button("Start Final Exam"):

                from modules.week6_final_exam import show_exam

                show_exam(user)

    # =================================================
    # CERTIFICATE
    # =================================================

    st.divider()

    st.subheader("🎖 Certificate")

    if has_certificate(user_id):

        st.success("Certificate issued")

    else:

        if can_issue_certificate(user_id):

            if st.button("Generate Certificate"):

                issue_certificate(user_id)

                st.success("Certificate generated")

    # =================================================
    # SIDEBAR
    # =================================================

    with st.sidebar:

        st.markdown("### 👩‍🎓 Student Menu")

        st.markdown(user["username"])

        completed = sum(1 for s in progress.values() if s=="completed")

        st.progress(completed/TOTAL_WEEKS)

        if st.button("Logout"):

            st.session_state.clear()

            st.rerun()
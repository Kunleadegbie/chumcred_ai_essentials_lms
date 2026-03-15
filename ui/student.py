import os
import streamlit as st

from services.progress import (
    get_progress,
    mark_week_completed,
)

from services.assignments import (
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
    # COURSE PROGRESS GRID
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

        with cols[(week - 1) % 3]:

            # ---------- WEEK BUTTON ----------
            if status != "locked":

                if st.button(label, key=f"week_btn_{week}"):

                    st.session_state["selected_week"] = week

                    st.rerun()

            else:

                st.button(label, disabled=True, key=f"week_btn_locked_{week}")

            # ---------- WEEK PROGRESS BAR ----------
            if status == "completed":

                st.progress(1.0)

                st.caption("Completed")

            elif status == "unlocked":

                st.progress(0.5)

                st.caption("In Progress")

            else:

                st.progress(0.0)

                st.caption("Locked")

    # =================================================
    # DISPLAY WEEK CONTENT
    # =================================================

    if "selected_week" in st.session_state:

        week = st.session_state["selected_week"]

        st.divider()

        st.subheader(f"📖 Week {week} Content")

        file_path = os.path.join(CONTENT_DIR, f"week{week}.md")

        if os.path.exists(file_path):

            with open(file_path, "r", encoding="utf-8") as f:

                st.markdown(f.read())

        else:

            st.warning("Content not yet uploaded for this week.")

        # ---------- MARK COMPLETED ----------
        if st.button("Mark Week as Completed", key=f"complete_week_{week}"):

            mark_week_completed(user_id, week)

            st.success(f"Week {week} marked as completed")

            st.rerun()

    # =================================================
    # FINAL EXAM
    # =================================================

    st.divider()
    st.subheader("📝 Final Exam")

    if "show_final_exam" not in st.session_state:

        st.session_state["show_final_exam"] = False

    with read_conn() as conn:

        row = conn.execute(
            """
            SELECT exam_unlocked, exam_reviewed
            FROM student_exam_status
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if not row or not row["exam_unlocked"]:

        st.warning(
            "Final exam will be unlocked by the administrator after Week 6 completion."
        )

    else:

        if row["exam_reviewed"]:

            st.error("You have already reviewed the exam answers. Exam locked.")

        else:

            st.success("Final exam unlocked. You can start the exam.")

            if st.button("Start Final Exam", key="start_final_exam_btn"):

                st.session_state["show_final_exam"] = True

                st.rerun()

    if st.session_state.get("show_final_exam", False):

        from modules.week6_final_exam import show_exam

        show_exam(user)

        return

    # =================================================
    # CERTIFICATE
    # =================================================

    st.divider()

    st.subheader("🎖 Certificate")

    if has_certificate(user_id):

        st.success("Certificate issued")

    else:

        if can_issue_certificate(user_id):

            if st.button("Generate Certificate", key="generate_certificate"):

                issue_certificate(user_id)

                st.success("Certificate generated")

    # =================================================
    # SIDEBAR
    # =================================================

    with st.sidebar:

        st.markdown("### 👩‍🎓 Student Menu")

        st.markdown(user["username"])

        completed = sum(1 for s in progress.values() if s == "completed")

        st.progress(completed / TOTAL_WEEKS)

        st.caption(f"{completed} of {TOTAL_WEEKS} weeks completed")

        if st.button("Logout"):

            st.session_state.clear()

            st.rerun()
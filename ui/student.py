# --------------------------------------------------
# ui/student.py
# --------------------------------------------------
# ==================================================
# ui/student.py
# ==================================================

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

from services.help import list_active_broadcasts
from services.certificates import has_certificate, issue_certificate


CONTENT_DIR = "content"
TOTAL_WEEKS = 6


# ==================================================
# ROUTER
# ==================================================

def student_router(user):

    user_id = user["id"]

    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user['username']}")


    # =================================================
    # WEEK 0 — ORIENTATION
    # =================================================

    if not is_orientation_completed(user_id):

        st.header("🧭 Orientation (Week 0)")

        md_path = os.path.join(CONTENT_DIR, "week0.md")

        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.warning("Orientation content not found.")

        if st.button(
            "✅ I have read and understood",
            key="orientation_done_btn"
        ):
            mark_orientation_completed(user_id)
            st.success("Orientation completed.")
            st.rerun()

        return


    # =================================================
    # BROADCAST
    # =================================================

    broadcasts = list_active_broadcasts(limit=1) or []

    if broadcasts:
        b = broadcasts[0]

        subject = b.get("subject") or "Announcement"
        message = b.get("message") or ""

        st.warning(f"📢 **{subject}**\n\n{message}")


    # =================================================
    # GRADE SUMMARY
    # =================================================

    st.subheader("📊 Your Grades")

    summary = get_student_grade_summary(user_id)

    cols = st.columns(3)

    for i, item in enumerate(summary):

        with cols[i % 3]:

            if item["status"] == "graded":

                st.metric(
                    f"Week {item['week']}",
                    f"{item['grade']}%",
                    item["badge"],
                )
            else:
                st.metric(f"Week {item['week']}", "Pending")

    st.divider()


    # =================================================
    # PROGRESS
    # =================================================

    progress = get_progress(user_id)


    # =================================================
    # WEEK CARDS
    # =================================================

    st.subheader("📘 Course Progress")

    cols = st.columns(3)

    selected_week = None

    for week in range(1, TOTAL_WEEKS + 1):

        status = progress.get(week, "locked")

        col = cols[(week - 1) % 3]

        with col:

            label = f"Week {week}"

            if status == "completed":
                label += " ✔️"
            elif status == "unlocked":
                label += " 🔓"
            else:
                label += " 🔒"

            grade, badge = get_week_grade(user_id, week)

            if grade is not None:
                st.caption(f"🏅 {grade}% — {badge}")

            if status != "locked":

                if st.button(label, key=f"week_btn_{week}"):
                    selected_week = week

            else:
                st.button(label, disabled=True)


    # =================================================
    # WEEK CONTENT + UPLOAD
    # =================================================

    if selected_week:

        st.divider()

        st.header(f"📘 Week {selected_week}")

        md_path = os.path.join(
            CONTENT_DIR,
            f"week{selected_week}.md"
        )

        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.error("Content not found.")
            return


        st.divider()

        grade, badge = get_week_grade(user_id, selected_week)

        if grade is not None:
            st.success(f"🏅 Grade: {grade}% — {badge}")
        else:
            st.info("Awaiting grading.")


        # =============================================
        # ASSIGNMENT FORM
        # =============================================

        st.subheader("📤 Assignment Submission")

        if has_assignment(user_id, selected_week):

            st.success("✅ Assignment already submitted.")

        else:

            with st.form(
                key=f"assign_form_{selected_week}",
                clear_on_submit=True,
            ):

                uploaded_file = st.file_uploader(
                    "Upload PDF",
                    type=["pdf"],
                    key=f"file_{selected_week}",
                )

                submit = st.form_submit_button(
                    "📨 Submit Assignment"
                )

                if submit:

                    if not uploaded_file:
                        st.error("Please upload a PDF file.")
                        st.stop()

                    save_assignment(
                        user_id,
                        selected_week,
                        uploaded_file,
                    )

                    mark_week_completed(
                        user_id,
                        selected_week
                    )

                    st.success("Submitted successfully.")
                    st.rerun()


    # =================================================
    # CERTIFICATE
    # =================================================

    st.divider()

    st.subheader("🎖 Certificate")

    if has_certificate(user_id):

        st.success("Certificate issued 🎉")

    else:

        if can_issue_certificate(user_id):

            st.info("All grades approved.")

            if st.button(
                "Generate Certificate",
                key="cert_btn"
            ):
                issue_certificate(user_id)
                st.rerun()

        else:
            st.warning("Complete all weeks first.")


    # =================================================
    # SIDEBAR
    # =================================================

    with st.sidebar:

        st.markdown("### 👩‍🎓 Student Menu")
        st.markdown(f"**User:** {user['username']}")

        completed = sum(
            1 for s in progress.values()
            if s == "completed"
        )

        st.progress(completed / TOTAL_WEEKS)

        if st.button(
            "🆘 Help & Support",
            key="help_btn"
        ):
            st.session_state["support_open"] = True

        if st.button(
            "🚪 Logout",
            key="logout_btn"
        ):
            st.session_state.clear()
            st.rerun()

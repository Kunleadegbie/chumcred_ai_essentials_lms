# --------------------------------------------------
# ui/student.py
# --------------------------------------------------
# --------------------------------------------------
# ui/student.py
# --------------------------------------------------
import os
import streamlit as st
from datetime import datetime

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

from services.broadcasts import (
    get_active_broadcasts,
    has_read,
    mark_as_read,
)

from services.certificates import has_certificate, issue_certificate

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


def student_router(user):
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user['username']}")

    user_id = user["id"]

    # =================================================
    # WEEK 0 — ORIENTATION (MANDATORY)
    # =================================================
    if not is_orientation_completed(user_id):
        st.header("🧭 Orientation (Week 0)")

        md_path = os.path.join(CONTENT_DIR, "week0.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.warning("Orientation content not found.")

        if st.button("✅ I have read and understood the Orientation"):
            mark_orientation_completed(user_id)
            mark_week_completed(user_id, 1)
            st.success("Orientation completed. Week 1 unlocked.")
            st.rerun()

        st.stop()

    # =================================================
    # BROADCASTS (Dismissible + Auto-Expire)
    # =================================================
    broadcasts = get_active_broadcasts()

    for b in broadcasts:
        if has_read(b["id"], user_id):
            continue

        st.info(f"📢 **{b['title']}**\n\n{b['message']}")

        if st.button("Got it", key=f"got_{b['id']}"):
            mark_as_read(b["id"], user_id)
            st.rerun()

        break  # show only one at a time

    # =================================================
    # GRADES SUMMARY
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

    # =================================================
    # COURSE PROGRESS
    # =================================================
    progress = get_progress(user_id)
    st.subheader("📘 Course Progress")

    if "selected_week" not in st.session_state:
        st.session_state["selected_week"] = None

    cols = st.columns(3)
    for week in range(1, TOTAL_WEEKS + 1):
        status = progress.get(week, "locked")

        with cols[(week - 1) % 3]:
            label = f"Week {week}"
            if status == "completed":
                label += " ✔️"
            elif status == "unlocked":
                label += " 🔓"
            else:
                label += " 🔒"

            if status != "locked":
                if st.button(label, key=f"w_{week}"):
                    st.session_state["selected_week"] = week
            else:
                st.button(label, disabled=True, key=f"w_{week}_disabled")

    # =================================================
    # WEEK CONTENT + ASSIGNMENT
    # =================================================
    selected_week = st.session_state.get("selected_week")
    if selected_week:
        st.divider()
        st.header(f"📘 Week {selected_week}")

        md_path = os.path.join(CONTENT_DIR, f"week{selected_week}.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)

        grade, badge = get_week_grade(user_id, selected_week)
        if grade is not None:
            st.success(f"🏅 Grade: {grade}% — {badge}")
        else:
            st.info("Awaiting grading.")

        st.subheader("📤 Assignment Submission")

        if has_assignment(user_id, selected_week):
            st.info("Assignment already submitted.")
        else:
            with st.form(key=f"assign_{selected_week}"):
                file = st.file_uploader("Upload PDF", type=["pdf"])
                submit = st.form_submit_button("Submit Assignment")

            if submit and file:
                save_assignment(user_id, selected_week, file)
                mark_week_completed(user_id, selected_week)
                st.success("Assignment submitted.")
                st.rerun()

    # =================================================
    # CERTIFICATE
    # =================================================
    st.divider()
    st.subheader("🎖 Certificate")

    if has_certificate(user_id):
        st.success("Certificate issued 🎉")
    elif can_issue_certificate(user_id):
        if st.button("Generate Certificate"):
            issue_certificate(user_id)
            st.rerun()

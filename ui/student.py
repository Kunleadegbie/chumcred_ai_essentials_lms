# --------------------------------------------------
# ui/student.py
# --------------------------------------------------
# --------------------------------------------------
# ui/student.py
# --------------------------------------------------
import os
import streamlit as st

from services.progress import (
    get_progress,
    mark_week_completed,
    is_orientation_completed,
    mark_orientation_completed,
    sync_user_progress,
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


def student_router(user):

    # Ensure DB progress is synced
    sync_user_progress(user["id"])

    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user['username']}")

    # =================================================
    # WEEK 0 (ORIENTATION) — MANDATORY LANDING
    # =================================================
    if not is_orientation_completed(user["id"]):
        st.header("🧭 Orientation (Week 0)")

        md_path = os.path.join(CONTENT_DIR, "week0.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.warning("Orientation content not found. Please contact admin.")

        if st.button("✅ I have read and understood the Orientation"):
            mark_orientation_completed(user["id"])
            st.success("Orientation completed. Week 1 is now unlocked.")
            st.rerun()

        return

    # =================================================
    # BROADCAST POPUP
    # =================================================
    broadcasts = list_active_broadcasts(limit=1) or []
    if broadcasts:
        b = broadcasts[0]
        subject = b["subject"] if "subject" in b.keys() else "Announcement"
        message = b["message"]
        st.warning(f"📢 **{subject}**\n\n{message}")

    # =================================================
    # DASHBOARD GRADES
    # =================================================
    st.subheader("📊 Your Grades")

    summary = get_student_grade_summary(user["id"]) or []
    cols = st.columns(3)

    for i, item in enumerate(summary):
        try:
            week = item["week"]
            status = item["status"]
            grade = item["grade"]
            badge = item["badge"]
        except Exception:
            continue

        with cols[i % 3]:
            if status == "graded":
                st.metric(f"Week {week}", f"{grade}%", badge)
            else:
                st.metric(f"Week {week}", "Pending")

    st.divider()

    # =================================================
    # LOAD PROGRESS
    # =================================================
    progress = get_progress(user["id"])

    # =================================================
    # COURSE WEEKS
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

            grade, badge = get_week_grade(user["id"], week)
            if grade is not None:
                st.caption(f"🏅 {grade}% — {badge}")

            if status != "locked":
                if st.button(label, key=f"w_{week}"):
                    selected_week = week
            else:
                st.button(label, disabled=True)

    # =================================================
    # WEEK CONTENT + ASSIGNMENT
    # =================================================
    if selected_week:

        st.divider()
        st.header(f"📘 Week {selected_week}")

        md_path = os.path.join(CONTENT_DIR, f"week{selected_week}.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.error("Week content not found.")
            return

        st.divider()

        grade, badge = get_week_grade(user["id"], selected_week)

        if grade is not None:
            st.success(f"🏅 **Grade:** {grade}% — **{badge}**")
        else:
            st.info("No grade yet (awaiting review).")

        st.subheader("📤 Assignment Submission")

        # ------------------------------
        # ✅ FIXED UPLOAD BLOCK
        # ------------------------------

        upload_key = f"upload_{selected_week}"

        if upload_key not in st.session_state:
            st.session_state[upload_key] = None

        if has_assignment(user["id"], selected_week):
            st.info("✅ Assignment submitted.")

        else:

            uploaded_file = st.file_uploader(
                "Upload assignment (PDF only)",
                type=["pdf"],
                key=f"file_{selected_week}",
            )

            if uploaded_file:
                st.session_state[upload_key] = uploaded_file

            if st.session_state[upload_key]:

                st.success(
                    f"Selected: {st.session_state[upload_key].name}"
                )

                if st.button("📤 Submit Assignment", key=f"submit_{selected_week}"):

                    save_assignment(
                        user["id"],
                        selected_week,
                        st.session_state[upload_key],
                    )

                    mark_week_completed(user["id"], selected_week)

                    st.session_state[upload_key] = None

                    st.success("Assignment submitted successfully.")
                    st.rerun()

    # =================================================
    # CERTIFICATE
    # =================================================
    st.divider()
    st.subheader("🎖 Certificate")

    if has_certificate(user["id"]):
        st.success("Certificate issued 🎉")

    else:
        if can_issue_certificate(user["id"]):

            st.info("All grades approved. Certificate ready.")

            if st.button("Generate Certificate"):
                issue_certificate(user["id"])
                st.rerun()

        else:
            st.warning(
                "Complete and pass all graded assignments to unlock certificate."
            )

    # =================================================
    # SIDEBAR
    # =================================================
    with st.sidebar:

        st.markdown("### 👩‍🎓 Student Menu")
        st.markdown(f"**User:** {user['username']}")

        completed = sum(1 for s in progress.values() if s == "completed")
        st.progress(completed / TOTAL_WEEKS)

        if st.button("🆘 Help & Support"):
            st.session_state["support_open"] = True

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()
            file = st.file_uploader(
                "Upload assignment (PDF only)",
                type=["pdf"],
                key=f"up_{selected_week}",
            )
            if file and st.button("Submit Assignment"):
                save_assignment(user["id"], selected_week, file)
                mark_week_completed(user["id"], selected_week)
                st.success("Assignment submitted successfully.")
                st.rerun()

    # =================================================
    # CERTIFICATE (STRICTLY AFTER ALL GRADES APPROVED)
    # =================================================
    st.divider()
    st.subheader("🎖 Certificate")

    if has_certificate(user["id"]):
        st.success("Certificate issued 🎉")
    else:
        if can_issue_certificate(user["id"]):
            st.info("All grades approved. Certificate ready.")
            if st.button("Generate Certificate"):
                issue_certificate(user["id"])
                st.rerun()
        else:
            st.warning(
                "Complete and pass all graded assignments to unlock certificate."
            )

    # =================================================
    # SIDEBAR
    # =================================================
    with st.sidebar:
        st.markdown("### 👩‍🎓 Student Menu")
        st.markdown(f"**User:** {user['username']}")

        completed = sum(1 for s in progress.values() if s == "completed")
        st.progress(completed / TOTAL_WEEKS)

        if st.button("🆘 Help & Support"):
            st.session_state["support_open"] = True

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

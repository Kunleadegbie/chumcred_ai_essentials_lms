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
)

from services.assignments import (
    save_assignment,
    has_assignment,
    get_week_grade,
    get_grade_summary,
    get_student_grade_summary,
)

from services.help import list_active_broadcasts

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


def student_router(user):
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

        # ⛔ Stop here until orientation is completed
        return

    # =================================================
    # BROADCAST POPUP (Dashboard)
    # =================================================
    broadcasts = list_active_broadcasts(limit=1) or []
    if broadcasts:
        b = broadcasts[0]
        subject = b["subject"] if "subject" in b.keys() else "Announcement"
        message = b["message"]
        st.warning(f"📢 **{subject}**\n\n{message}")

    # =================================================
    # LOAD PROGRESS
    # =================================================
    progress = get_progress(user["id"])

    # =================================================
    # DASHBOARD GRADE SUMMARY (Option #2)
    # =================================================
    summary = get_student_grade_summary(user["id"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("✅ Weeks Passed", summary["passed"])
    with c2:
        st.metric("🏅 Merit", summary["merit"])
    with c3:
        st.metric("🏆 Distinction", summary["distinction"])

    st.divider()

    # =================================================
    # COURSE WEEK CARDS
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
    # WEEK CONTENT + ASSIGNMENT + GRADE
    # =================================================
    if selected_week:
        st.divider()
        st.header(f"📘 Week {selected_week}")

        md_path = os.path.join(CONTENT_DIR, f"week{selected_week}.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.error("Week content not found. Please contact admin.")
            return

        st.divider()

        grade, badge = get_week_grade(user["id"], selected_week)
        if grade is not None:
            st.success(f"🏅 **Grade:** {grade}% — **{badge}**")
        else:
            st.info("No grade yet for this week (awaiting admin review).")

        st.subheader("📤 Assignment Submission")

        if has_assignment(user["id"], selected_week):
            st.info("✅ Assignment submitted.")
        else:
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

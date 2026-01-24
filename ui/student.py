# --------------------------------------------------
# ui/student.py
# --------------------------------------------------
# ui/student.py
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
)
from services.help import list_active_broadcasts

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


def student_router(user):
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user['username']}")

    # -------------------------------------------------
    # Broadcast (popup style)
    # -------------------------------------------------
    broadcasts = list_active_broadcasts(limit=1) or []
    if broadcasts:
        b = broadcasts[0]
        st.warning(f"📢 **{b['subject'] or 'Announcement'}**\n\n{b['message']}")

    # -------------------------------------------------
    # Progress
    # -------------------------------------------------
    progress = get_progress(user["id"])

    # -------------------------------------------------
    # WEEK 0 — ORIENTATION (MANDATORY)
    # -------------------------------------------------
    if not is_orientation_completed(user["id"]):
        st.header("📘 Week 0 — Orientation")

        md_path = os.path.join(CONTENT_DIR, "week0.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)

        if st.button("✅ Mark Orientation Completed"):
            mark_orientation_completed(user["id"])
            st.success("Orientation completed. You may now proceed to Week 1.")
            st.rerun()
        return

    # -------------------------------------------------
    # Week Cards
    # -------------------------------------------------
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

            if status != "locked":
                if st.button(label, key=f"w_{week}"):
                    selected_week = week
            else:
                st.button(label, disabled=True)

    # -------------------------------------------------
    # Week Content
    # -------------------------------------------------
    if selected_week:
        st.divider()
        st.header(f"📘 Week {selected_week}")

        md_path = os.path.join(CONTENT_DIR, f"week{selected_week}.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)

        # -----------------------------
        # Grade display
        # -----------------------------
        grade, badge = get_week_grade(user["id"], selected_week)
        if grade is not None:
            st.success(f"🏅 **Grade:** {grade}% — **{badge}**")

        # -----------------------------
        # Assignment
        # -----------------------------
        st.subheader("📤 Assignment Submission")

        if has_assignment(user["id"], selected_week):
            st.info("Assignment submitted.")
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

    # -------------------------------------------------
    # Sidebar
    # -------------------------------------------------
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

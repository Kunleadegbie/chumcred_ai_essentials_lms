

# --------------------------------------------------
# ui/student.py
# --------------------------------------------------
# ui/student.py

import os
import streamlit as st

from services.progress import (
    get_progress,
    mark_week_completed,
)

from services.assignments import (
    save_assignment,
    has_assignment,
)

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


def student_router(user):
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user['username']}")

    progress = get_progress(user["id"])
    selected_week = None

    st.divider()
    st.subheader("📘 Course Progress")

    cols = st.columns(3)

    # -----------------------------
    # WEEK CARDS (INCLUDING WEEK 0)
    # -----------------------------
    for week in range(0, TOTAL_WEEKS + 1):
        status = progress.get(week, "locked")
        col = cols[week % 3]

        label = "Orientation (Week 0)" if week == 0 else f"Week {week}"

        with col:
            if status in ("unlocked", "completed"):
                if st.button(
                    f"{label} {'✔️' if status == 'completed' else '➡️'}",
                    key=f"week_{week}",
                ):
                    selected_week = week
            else:
                st.button(f"{label} 🔒", disabled=True)

    st.divider()

    # -----------------------------
    # WEEK CONTENT
    # -----------------------------
    if selected_week is not None:
        st.header("📖 Orientation" if selected_week == 0 else f"📘 Week {selected_week}")

        md_path = os.path.join(CONTENT_DIR, f"week{selected_week}.md")

        if not os.path.exists(md_path):
            st.error("Content not found.")
            return

        with open(md_path, encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)

        st.divider()

        # -----------------------------
        # WEEK 0 COMPLETION GATE
        # -----------------------------
        if selected_week == 0:
            if progress.get(0) != "completed":
                if st.button("✅ Mark Orientation Completed"):
                    mark_week_completed(user["id"], 0)
                    st.success("Orientation completed. You may proceed once Week 1 is unlocked by admin.")
                    st.rerun()
            else:
                st.success("Orientation already completed.")

        # -----------------------------
        # ASSIGNMENTS (WEEK 1–6 ONLY)
        # -----------------------------
        elif selected_week >= 1:
            st.subheader("📤 Assignment Submission")

            if has_assignment(user["id"], selected_week):
                st.success("Assignment already submitted.")
            else:
                uploaded = st.file_uploader(
                    "Upload assignment (PDF only)",
                    type=["pdf"],
                    key=f"upload_{selected_week}",
                )

                if uploaded and st.button("Submit Assignment"):
                    save_assignment(user["id"], selected_week, uploaded)
                    st.success("Assignment submitted.")
                    st.rerun()

    # -----------------------------
    # SIDEBAR
    # -----------------------------
    with st.sidebar:
        st.markdown("### 👩‍🎓 Student Menu")
        st.markdown(f"**User:** {user['username']}")

        completed = sum(1 for s in progress.values() if s == "completed")
        st.progress(completed / (TOTAL_WEEKS + 1))

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

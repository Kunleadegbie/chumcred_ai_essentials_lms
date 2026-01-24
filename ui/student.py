

# --------------------------------------------------
# ui/student.py
# --------------------------------------------------

from __future__ import annotations

import os
import streamlit as st

from services.progress import (
    get_progress,
    mark_week_completed,
    is_week_unlocked,
)
from services.assignments import save_assignment, has_assignment
from ui.help import help_router
from services.help import list_active_broadcasts

CONTENT_DIR = "content"
TOTAL_WEEKS = 6
ORIENTATION_WEEK = 0


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _logo_path():
    candidates = [
        os.path.join("assets", "logo.png"),
        "logo.png",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _read_md(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# -------------------------------------------------
# Main Student Router
# -------------------------------------------------
def student_router(user):
    # Persist navigation
    if "student_view" not in st.session_state:
        st.session_state.student_view = "dashboard"  # dashboard | help

    # Load progress
    progress = get_progress(user["id"])

    # -------------------------------------------------
    # Sidebar (RESTORED)
    # -------------------------------------------------
    with st.sidebar:
        logo = _logo_path()
        if logo:
            st.image(logo, width=160)

        st.markdown("### 👩‍🎓 Student Menu")
        st.markdown(f"**User:** {user.get('username', '')}")

        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.student_view = "dashboard"
            st.rerun()

        if st.button("🆘 Help & Support", use_container_width=True):
            st.session_state.student_view = "help"
            st.rerun()

        completed = sum(
            1 for w in range(1, TOTAL_WEEKS + 1)
            if progress.get(w) == "completed"
        )
        st.progress(completed / TOTAL_WEEKS)

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # -------------------------------------------------
    # Route to Help
    # -------------------------------------------------
    if st.session_state.student_view == "help":
        help_router(user, role="student")
        return

    # -------------------------------------------------
    # Dashboard Header
    # -------------------------------------------------
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user.get('username', '')}")
    st.divider()

    # -------------------------------------------------
    # 📢 Broadcast Popup (FIXED)
    # -------------------------------------------------
    broadcasts = list_active_broadcasts()

    if broadcasts:
        latest = broadcasts[0]
        dismiss_key = f"broadcast_dismissed_{latest['id']}"

        if not st.session_state.get(dismiss_key, False):
            st.warning(
                f"""
### 📢 Announcement from Admin

**{latest.get('subject') or 'Important Notice'}**

{latest.get('message')}
"""
            )
            if st.button("Got it"):
                st.session_state[dismiss_key] = True
                st.rerun()

    # -------------------------------------------------
    # FORCE Week 0 until completed
    # -------------------------------------------------
    if "selected_week" not in st.session_state:
        st.session_state.selected_week = ORIENTATION_WEEK

    if progress.get(ORIENTATION_WEEK) != "completed":
        st.session_state.selected_week = ORIENTATION_WEEK

    # -------------------------------------------------
    # Week Cards
    # -------------------------------------------------
    st.subheader("📘 Course Progress")
    cols = st.columns(3)

    all_weeks = [ORIENTATION_WEEK] + list(range(1, TOTAL_WEEKS + 1))

    for idx, week in enumerate(all_weeks):
        col = cols[idx % 3]
        status = progress.get(week, "locked")

        with col:
            if week == ORIENTATION_WEEK:
                label = "Orientation (Week 0)"
                icon = "✔️" if status == "completed" else "✅"
                if st.button(f"{label} {icon}", key="week_0"):
                    st.session_state.selected_week = ORIENTATION_WEEK
                    st.rerun()
                st.caption("Mandatory")
            else:
                if is_week_unlocked(user["id"], week):
                    icon = "✔️" if status == "completed" else "✅"
                    if st.button(f"Week {week} {icon}", key=f"week_{week}"):
                        st.session_state.selected_week = week
                        st.rerun()
                else:
                    st.button(f"Week {week} 🔒", disabled=True)

    st.divider()

    # -------------------------------------------------
    # Render Selected Week
    # -------------------------------------------------
    selected_week = st.session_state.selected_week

    # ------------------ Week 0 ------------------
    if selected_week == ORIENTATION_WEEK:
        st.header("📘 Week 0 — Orientation (Mandatory)")

        md_path = os.path.join(CONTENT_DIR, "week0.md")
        content = _read_md(md_path)

        if not content:
            st.warning("Week 0 content not found. Add `content/week0.md`.")
        else:
            st.markdown(content, unsafe_allow_html=True)

        st.divider()

        if progress.get(ORIENTATION_WEEK) == "completed":
            st.success("✅ Orientation completed. You may proceed to Week 1 (if unlocked).")
        else:
            if st.button("✅ Mark Orientation Completed"):
                mark_week_completed(user["id"], ORIENTATION_WEEK)
                st.success("Orientation completed. Await admin unlock for Week 1.")
                st.rerun()

        return

    # ------------------ Week 1–6 ------------------
    if not is_week_unlocked(user["id"], selected_week):
        st.warning("This week is locked. Please wait for Admin to unlock it.")
        return

    st.header(f"📘 Week {selected_week}")

    md_path = os.path.join(CONTENT_DIR, f"week{selected_week}.md")
    content = _read_md(md_path)

    if not content:
        st.error("Week content not found. Please contact admin.")
        return

    st.markdown(content, unsafe_allow_html=True)
    st.divider()

    # -------------------------------------------------
    # Assignment Submission
    # -------------------------------------------------
    st.subheader("📤 Assignment Submission")

    if has_assignment(user["id"], selected_week):
        st.success("✅ Assignment already submitted.")
        st.info("Grade and feedback will appear after admin review.")
    else:
        uploaded_file = st.file_uploader(
            "Upload your assignment (PDF only)",
            type=["pdf"],
            key=f"upload_week_{selected_week}",
        )

        if uploaded_file and st.button("Submit Assignment"):
            save_assignment(user["id"], selected_week, uploaded_file)
            st.success("🎉 Assignment submitted successfully.")
            st.rerun()

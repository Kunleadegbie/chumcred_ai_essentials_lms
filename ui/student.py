

# --------------------------------------------------
# ui/student.py
# --------------------------------------------------

from __future__ import annotations

import os
import streamlit as st

from services.progress import get_progress, mark_week_completed, is_week_unlocked
from services.assignments import save_assignment, has_assignment
from ui.help import help_router  # assumes you already have ui/help.py

CONTENT_DIR = "content"
TOTAL_WEEKS = 6
ORIENTATION_WEEK = 0


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


def student_router(user):
    # Persist the current student view tab/page
    if "student_view" not in st.session_state:
        st.session_state.student_view = "dashboard"  # dashboard | help

    progress = get_progress(user["id"])

    # ---- Sidebar (RESTORE Help & Support + Logout) ----
    with st.sidebar:
        lp = _logo_path()
        if lp:
            st.image(lp, width=170)

        st.markdown("### 👩‍🎓 Student Menu")
        st.markdown(f"**User:** {user.get('username','')}")

        # Navigation
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.student_view = "dashboard"
            st.rerun()

        if st.button("🆘 Help & Support", use_container_width=True):
            st.session_state.student_view = "help"
            st.rerun()

        # Progress bar: count completed in Week 1..6 only (exclude Week 0)
        completed = sum(1 for w in range(1, TOTAL_WEEKS + 1) if progress.get(w) == "completed")
        st.progress(completed / TOTAL_WEEKS)

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # ---- Route to Help if selected ----
    if st.session_state.student_view == "help":
        help_router(user, role="student")
        return

    # ---- Main Dashboard ----
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user.get('username','')}")

    st.divider()

    # ===============================
    # FORCE LANDING ON WEEK 0 UNTIL COMPLETED
    # ===============================
    if "selected_week" not in st.session_state:
        st.session_state.selected_week = ORIENTATION_WEEK

    # If Week 0 not completed, force view to Week 0
    if progress.get(ORIENTATION_WEEK) != "completed":
        st.session_state.selected_week = ORIENTATION_WEEK

    # ===============================
    # WEEK SELECTION (CARDS)
    # ===============================
    st.subheader("📘 Course Progress")

    cols = st.columns(3)

    def week_label(week: int) -> str:
        return "Orientation (Week 0)" if week == ORIENTATION_WEEK else f"Week {week}"

    # Show Week 0 + Week 1..6
    all_weeks = [ORIENTATION_WEEK] + list(range(1, TOTAL_WEEKS + 1))

    for idx, week in enumerate(all_weeks):
        status = progress.get(week, "locked")
        col = cols[idx % 3]

        with col:
            # Week 0 is always clickable
            if week == ORIENTATION_WEEK:
                if status == "completed":
                    if st.button("Week 0 ✔️", key="week_0"):
                        st.session_state.selected_week = ORIENTATION_WEEK
                        st.rerun()
                else:
                    if st.button("Week 0 ✅", key="week_0"):
                        st.session_state.selected_week = ORIENTATION_WEEK
                        st.rerun()
                st.caption("Orientation (Mandatory)")
                continue

            # Weeks 1..6
            if is_week_unlocked(user["id"], week):
                icon = "✔️" if status == "completed" else "✅"
                if st.button(f"Week {week} {icon}", key=f"week_{week}"):
                    st.session_state.selected_week = week
                    st.rerun()
            else:
                st.button(f"Week {week} 🔒", disabled=True, key=f"week_{week}_locked")

    st.divider()

    # ===============================
    # WEEK CONTENT RENDERING
    # ===============================
    selected_week = st.session_state.selected_week

    # Week 0 content
    if selected_week == ORIENTATION_WEEK:
        st.header("📘 Week 0 — Orientation (Mandatory)")

        md_path = os.path.join(CONTENT_DIR, "week0.md")
        content = _read_md(md_path)

        if not content:
            st.warning("Week 0 content file not found. Please add: content/week0.md")
        else:
            st.markdown(content, unsafe_allow_html=True)

        st.divider()

        if progress.get(ORIENTATION_WEEK) == "completed":
            st.success("✅ Orientation completed. You can now access Week 1 (if unlocked).")
            # Week 1 will be unlocked automatically by mark_week_completed(0)
            if st.button("Go to Week 1"):
                st.session_state.selected_week = 1
                st.rerun()
        else:
            st.info("Please read the orientation content, then confirm completion to unlock Week 1.")
            if st.button("✅ Mark Orientation Completed"):
                mark_week_completed(user["id"], ORIENTATION_WEEK)
                st.success("Orientation completed. Week 1 is now unlocked.")
                st.session_state.selected_week = 1
                st.rerun()

        return

    # Weeks 1..6 content
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

    # ===============================
    # ASSIGNMENT SUBMISSION (WEEK 1–6)
    # ===============================
    st.subheader("📤 Assignment Submission")

    if has_assignment(user["id"], selected_week):
        st.success("✅ Assignment already submitted.")
        st.info("You can view your grade and feedback after admin review.")
    else:
        uploaded_file = st.file_uploader(
            "Upload your assignment (PDF only)",
            type=["pdf"],
            key=f"upload_week_{selected_week}",
        )

        if uploaded_file:
            if st.button("Submit Assignment", key=f"submit_{selected_week}"):
                save_assignment(user["id"], selected_week, uploaded_file)
                # IMPORTANT: Do NOT auto-unlock next week here (admin controls Week 2–6)
                st.success("🎉 Assignment submitted successfully!")
                st.rerun()


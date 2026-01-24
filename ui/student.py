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
    get_grade_summary,
)
from services.help import list_active_broadcasts

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


# -------------------------------------------------
# FORCE WEEK 0 (ORIENTATION) LANDING
# -------------------------------------------------
from services.progress import is_orientation_completed, mark_orientation_completed

def student_router(user):
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user['username']}")

    # ---------------------------------------------
    # FORCE WEEK 0 (ORIENTATION) — MANDATORY
    # ---------------------------------------------
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

        # ⛔ STOP rendering anything else
        return


    # -------------------------------------------------
    # Broadcast (popup style)
    # -------------------------------------------------
    broadcasts = list_active_broadcasts(limit=1) or []
    if broadcasts:
        b = broadcasts[0]
        subject = b["subject"] if "subject" in b.keys() else None
        message = b["message"] if "message" in b.keys() else ""
        st.warning(f"📢 **{subject or 'Announcement'}**\n\n{message}")

    # -------------------------------------------------
    # Progress
    # -------------------------------------------------
    progress = get_progress(user["id"])


# -------------------------------------------------
# DASHBOARD GRADE SUMMARY
# -------------------------------------------------
from services.assignments import get_student_grade_summary

summary = get_student_grade_summary(user["id"])

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("✅ Weeks Passed", summary["passed"])

with col2:
    st.metric("🏅 Merit", summary["merit"])

with col3:
    st.metric("🏆 Distinction", summary["distinction"])



    # -------------------------------------------------
    # WEEK 0 — ORIENTATION (MANDATORY CLICK-THROUGH)
    # -------------------------------------------------
    if not is_orientation_completed(user["id"]):
        st.header("📘 Week 0 — Orientation")

        md_path = os.path.join(CONTENT_DIR, "week0.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.info("Orientation content (week0.md) not found in content/ folder.")

        if st.button("✅ Mark Orientation Completed"):
            mark_orientation_completed(user["id"])
            st.success("Orientation completed. You may now proceed to Week 1.")
            st.rerun()
        return

    # -------------------------------------------------
    # Dashboard Grade Summary Tiles (Option #2)
    # -------------------------------------------------
    summary = get_grade_summary(user["id"])
    completed_weeks = sum(1 for s in progress.values() if s == "completed")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Completed Weeks", f"{completed_weeks}/{TOTAL_WEEKS}")
    with c2:
        avg = summary["avg_grade"]
        st.metric("Average Grade", "-" if avg is None else f"{avg:.1f}%")
    with c3:
        st.metric("Best Badge", summary["best_badge"] or "-")
    with c4:
        latest = summary["latest_grade"]
        latest_badge = summary["latest_badge"]
        st.metric("Latest Result", "-" if latest is None else f"{latest}% ({latest_badge})")

    st.divider()

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

            # show grade badge on card (if available)
            g, badge = get_week_grade(user["id"], week)
            if g is not None and badge is not None:
                st.caption(f"🏅 {g}% — {badge}")

            if status != "locked":
                if st.button(label, key=f"w_{week}"):
                    selected_week = week
            else:
                st.button(label, disabled=True)

    # -------------------------------------------------
    # Week Content + Grade + Assignment
    # -------------------------------------------------
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

        # Grade display (inside week)
        grade, badge = get_week_grade(user["id"], selected_week)
        if grade is not None:
            st.success(f"🏅 **Grade:** {grade}% — **{badge}**")
        else:
            st.info("No grade yet for this week (admin will grade after review).")

        # Assignment submission
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

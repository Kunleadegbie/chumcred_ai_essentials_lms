# --------------------------------------------------
# ui/student.py
# --------------------------------------------------

# ui/student.py
import os
import streamlit as st

from services.progress import (
    get_progress,
    mark_week_completed,
    mark_orientation_completed,
)

from services.assignments import (
    save_assignment,
    has_assignment,
    list_student_assignments,
    get_assignment_for_week,
    get_week_grade,
)

from services.help import list_active_broadcasts
from ui.help import help_router

CONTENT_DIR = "content"
TOTAL_WEEKS = 6
ORIENTATION_WEEK = 0


def student_router(user):
    # ---------------- SIDEBAR ----------------
    with st.sidebar:
        st.markdown("### 👩‍🎓 Student Menu")
        menu = st.radio("Navigate", ["Dashboard", "Help & Support"])

        st.divider()
        st.markdown("### 📊 My Grades")
        rows = list_student_assignments(user["id"])
        if rows:
            for r in rows:
                grade = r["grade"] if r["grade"] is not None else "Pending"
                st.write(f"Week {r['week']} — {grade}")
        else:
            st.caption("No graded assignments yet.")

        st.divider()
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    if menu == "Help & Support":
        help_router(user, role="student")
        return

    # ---------------- DASHBOARD ----------------
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, **{user['username']}**")

    progress = get_progress(user["id"])

    # ---------------- BROADCAST POPUP ----------------
    broadcasts = list_active_broadcasts(limit=1)
    if broadcasts:
        b = broadcasts[0]
        key = f"dismiss_broadcast_{b['id']}"
        if not st.session_state.get(key):
            st.warning(f"### 📢 {b['subject']}\n\n{b['message']}")
            if st.button("Got it"):
                st.session_state[key] = True
                st.rerun()

    st.divider()

    # ---------------- WEEK SELECTION ----------------
    if "selected_week" not in st.session_state:
        st.session_state.selected_week = ORIENTATION_WEEK

    if progress.get(ORIENTATION_WEEK) != "completed":
        st.session_state.selected_week = ORIENTATION_WEEK

    weeks = [0] + list(range(1, TOTAL_WEEKS + 1))
    cols = st.columns(3)

    for i, week in enumerate(weeks):
        status = progress.get(week, "locked")
        label = "Orientation (Week 0)" if week == 0 else f"Week {week}"

        with cols[i % 3]:
            if week == 0 or status in ("unlocked", "completed"):
                if st.button(label, key=f"week_{week}"):
                    st.session_state.selected_week = week
            else:
                st.button(f"{label} 🔒", disabled=True)

    st.divider()

    wk = st.session_state.selected_week
    st.header("Orientation" if wk == 0 else f"Week {wk}")

    # ---------------- CONTENT ----------------
    path = os.path.join(CONTENT_DIR, "week0.md" if wk == 0 else f"week{wk}.md")
    if not os.path.exists(path):
        st.error("Content not found.")
        return

    with open(path, encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)

    st.divider()

    # ---------------- ORIENTATION COMPLETION ----------------
    if wk == 0:
        if progress.get(0) == "completed":
            st.success("✅ Orientation completed.")
        else:
            if st.button("✅ Mark Orientation Completed"):
                mark_orientation_completed(user["id"])
                st.success("Orientation completed. Await admin unlock for Week 1.")
                st.rerun()
        return

    # ---------------- ASSIGNMENT ----------------
    if progress.get(wk) != "unlocked":
        st.info("🔒 This week is locked by admin.")
        return

    assignment = get_assignment_for_week(user["id"], wk)

    if assignment:
        st.subheader("📤 Assignment Status")
        if assignment["status"] == "reviewed":
            st.success("✅ Reviewed")
            st.markdown(f"**Grade:** {assignment['grade']} / 100")
            if assignment["feedback"]:
                st.markdown(f"**Feedback:** {assignment['feedback']}")
            st.caption(f"Reviewed on: {assignment['reviewed_at']}")
        else:
            st.info("⏳ Submitted — awaiting review")
    else:
        file = st.file_uploader("Upload assignment (PDF)", type=["pdf"])
        if file and st.button("Submit Assignment"):
            save_assignment(user["id"], wk, file)
            mark_week_completed(user["id"], wk)
            st.success("Assignment submitted.")
            st.rerun()

    # ---------------- WEEK GRADE SUMMARY ----------------
    grade = get_week_grade(user["id"], wk)
    if grade is not None:
        st.success(f"🏅 Your grade for Week {wk}: {grade}")

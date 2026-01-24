

# --------------------------------------------------
# ui/student.py
# --------------------------------------------------

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
    get_week_grade,
)

# Broadcasts + Help Desk live in services/help.py (NOT ui/help.py)
from services.help import (
    list_active_broadcasts,
)

from ui.help import help_router  # your existing help page router (UI layer)


CONTENT_DIR = "content"
TOTAL_WEEKS = 6
ORIENTATION_WEEK = 0


def _safe_row_value(row, key, default=None):
    """
    Works for sqlite3.Row or dict.
    Prevents: AttributeError: 'sqlite3.Row' object has no attribute 'get'
    """
    try:
        # sqlite3.Row supports row["col"]
        val = row[key]
        return default if val is None else val
    except Exception:
        pass

    try:
        # dict supports .get()
        val = row.get(key, default)
        return default if val is None else val
    except Exception:
        return default


def _logo_path():
    candidates = [
        os.path.join("assets", "logo.png"),
        "logo.png",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _read_week_md(week: int) -> str:
    filename = "week0.md" if week == ORIENTATION_WEEK else f"week{week}.md"
    md_path = os.path.join(CONTENT_DIR, filename)
    if not os.path.exists(md_path):
        return ""
    with open(md_path, "r", encoding="utf-8") as f:
        return f.read()


def student_router(user):
    # ----------------------------
    # Sidebar (Navigation)
    # ----------------------------
    with st.sidebar:
        lp = _logo_path()
        if lp:
            st.image(lp, width=160)

        st.markdown("### 👩‍🎓 Student Menu")
        st.caption(f"User: **{user.get('username', '')}**")

        menu = st.radio(
            "Navigate",
            ["Dashboard", "Help & Support"],
            index=0,
            key="student_menu",
        )

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    # Help page is separate UI
    if menu == "Help & Support":
        help_router(user, role="student")
        return

    # ----------------------------
    # Dashboard
    # ----------------------------
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, **{user.get('username', '')}**")

    # Progress dict: {0:'unlocked/completed', 1:'locked/unlocked/completed', ...}
    progress = get_progress(user["id"])

    # ----------------------------
    # Broadcast Popup (Admin → Students)
    # ----------------------------
    broadcasts = list_active_broadcasts(limit=5) or []
    if broadcasts:
        latest = broadcasts[0]  # most recent

        b_id = _safe_row_value(latest, "id", None)
        b_subject = _safe_row_value(latest, "subject", "Important Notice")
        b_message = _safe_row_value(latest, "message", "")

        if b_id is not None:
            dismiss_key = f"broadcast_dismissed_{b_id}"
            if not st.session_state.get(dismiss_key, False):
                st.warning(
                    f"""
### 📢 Announcement from Admin

**{b_subject}**

{b_message}
"""
                )
                if st.button("Got it", key=f"dismiss_broadcast_{b_id}"):
                    st.session_state[dismiss_key] = True
                    st.rerun()

    st.divider()

    # ----------------------------
    # Enforce Week 0 mandatory click-through
    # ----------------------------
    # Week 0 should always be accessible
    # Week 1..6 should be locked until Admin unlocks,
    # BUT Week 1 must ALSO be blocked until Week 0 is completed.

    if "selected_week" not in st.session_state:
        st.session_state.selected_week = ORIENTATION_WEEK

    # Force landing on Week 0 until completed
    if progress.get(ORIENTATION_WEEK) != "completed":
        st.session_state.selected_week = ORIENTATION_WEEK

    # ----------------------------
    # Course Progress Cards (Week 0 + Week 1..6)
    # ----------------------------
    st.subheader("📘 Course Progress")

    cols = st.columns(3)
    all_weeks = [ORIENTATION_WEEK] + list(range(1, TOTAL_WEEKS + 1))

    def week_label(w: int) -> str:
        return "Orientation (Week 0)" if w == ORIENTATION_WEEK else f"Week {w}"

    for idx, week in enumerate(all_weeks):
        status = progress.get(week, "locked")
        col = cols[idx % 3]

        with col:
            # Week 0 always clickable
            if week == ORIENTATION_WEEK:
                if st.button("Orientation ✅" if status == "completed" else "Orientation", key=f"wk_{week}"):
                    st.session_state.selected_week = week
            else:
                # Week 1..6: locked unless admin unlocked
                if status == "completed":
                    if st.button(f"{week_label(week)} ✔️", key=f"wk_{week}"):
                        st.session_state.selected_week = week
                elif status == "unlocked":
                    # Extra guard: Week 1 stays blocked until Week 0 completed
                    if week == 1 and progress.get(ORIENTATION_WEEK) != "completed":
                        st.button(f"{week_label(week)} 🔒", disabled=True, key=f"wk_lock_{week}")
                    else:
                        if st.button(f"{week_label(week)} ✅", key=f"wk_{week}"):
                            st.session_state.selected_week = week
                else:
                    st.button(f"{week_label(week)} 🔒", disabled=True, key=f"wk_lock_{week}")

    st.divider()

    selected_week = st.session_state.get("selected_week", ORIENTATION_WEEK)

    # ----------------------------
    # Render Week Content
    # ----------------------------
    st.header("📘 Orientation (Week 0)" if selected_week == ORIENTATION_WEEK else f"📘 Week {selected_week}")

    md = _read_week_md(selected_week)
    if not md:
        st.error("Week content not found. Please contact admin.")
        return

    st.markdown(md, unsafe_allow_html=True)

    st.divider()

    # ----------------------------
    # Orientation completion button (Week 0 only)
    # ----------------------------
    if selected_week == ORIENTATION_WEEK:
        if progress.get(ORIENTATION_WEEK) == "completed":
            st.success("✅ Orientation completed.")
        else:
            if st.button("✅ Mark Orientation Completed", key="mark_orientation_completed"):
                mark_orientation_completed(user["id"])
                st.success("Orientation marked as completed. You can now access Week 1 once Admin unlocks it.")
                st.rerun()
        return

    # ----------------------------
    # Assignment Submission (Week 1..6)
    # ----------------------------
    st.subheader("📤 Assignment Submission")

    # If week is not unlocked by admin, don't allow upload
    if progress.get(selected_week) not in ("unlocked", "completed"):
        st.info("This week is locked. Please wait for Admin to unlock it.")
        return

    # If already submitted
    if has_assignment(user["id"], selected_week):
        st.success("✅ Assignment already submitted.")
    else:
        uploaded_file = st.file_uploader(
            "Upload your assignment (PDF only)",
            type=["pdf"],
            key=f"upload_week_{selected_week}",
        )

        if uploaded_file and st.button("Submit Assignment", key=f"submit_week_{selected_week}"):
            save_assignment(user["id"], selected_week, uploaded_file)

            # IMPORTANT: do NOT auto-unlock next week here.
            # Completion is recorded; admin controls unlocking of next weeks.
            mark_week_completed(user["id"], selected_week)

            st.success("🎉 Assignment submitted successfully! You can review it below.")
            st.rerun()

    st.divider()

    # ----------------------------
    # Grades / Submissions Table (Student View)
    # ----------------------------
    st.subheader("📑 Your Submissions & Grades")

    rows = list_student_assignments(user["id"]) or []
    if not rows:
        st.info("No assignment submissions yet.")
    else:
        table = []
        for r in rows:
            wk = _safe_row_value(r, "week", "")
            status = _safe_row_value(r, "status", "")
            submitted_at = _safe_row_value(r, "submitted_at", "")
            grade = _safe_row_value(r, "grade", "")
            table.append(
                {
                    "Week": wk,
                    "Status": status,
                    "Submitted At": submitted_at,
                    "Grade": grade if grade is not None else "",
                }
            )
        st.dataframe(table, use_container_width=True)

    # Show current week grade (if exists)
    g = get_week_grade(user["id"], selected_week)
    if g is not None:
        st.success(f"✅ Your grade for Week {selected_week}: **{g}**")

    st.divider()

    # ----------------------------
    # Transcript + Certificate (buttons can exist even if files aren’t ready)
    # ----------------------------
    st.subheader("📜 Documents")

    col1, col2 = st.columns(2)
    with col1:
        st.info("Transcript: available after admin review/approval (if configured).")
        st.button("⬇️ Download Transcript", disabled=True)

    with col2:
        st.info("Certificate: available only after Week 6 completion + admin issuance (if configured).")
        st.button("🎖 Download Certificate", disabled=True)

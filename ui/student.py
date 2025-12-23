# ui/student.py
import os
import streamlit as st

from services.progress import get_progress
from services.assignments import save_assignment, get_assignment, list_student_assignments
from ui.help import help_router

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


def student_router(user: dict):
    # -----------------------------
    # SIDEBAR (routes first)
    # -----------------------------
    with st.sidebar:
        # safer logo handling (supports either project root or assets/)
        if os.path.exists("logo.png"):
            st.image("logo.png", width=150)
        elif os.path.exists(os.path.join("assets", "logo.png")):
            st.image(os.path.join("assets", "logo.png"), width=150)

        st.markdown("### 👩‍🎓 Student Menu")
        st.markdown(f"**User:** {user['username']}")

        menu = st.radio("Navigate", ["Dashboard", "Help"], index=0)

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Route to Help page
    if menu == "Help":
        help_router(user, role="student")
        return

    # -----------------------------
    # MAIN PAGE
    # -----------------------------
    st.title("🎓 AI Essentials — Student Dashboard")
    st.caption(f"Welcome, {user['username']}")

    progress = get_progress(user["id"])  # {1:'unlocked', 2:'locked', ...}

    # keep selected week across reruns
    if "selected_week" not in st.session_state:
        st.session_state["selected_week"] = None

    st.divider()

    st.subheader("📘 Course Progress")

    # Progress bar (completed weeks only)
    completed_count = sum(1 for w in progress.values() if w == "completed")
    st.progress(completed_count / TOTAL_WEEKS if TOTAL_WEEKS else 0)

    cols = st.columns(3)
    for week in range(1, TOTAL_WEEKS + 1):
        status = progress.get(week, "locked")
        col = cols[(week - 1) % 3]

        with col:
            label = f"Week {week}"
            if status == "completed":
                clicked = st.button(f"{label} ✔️", key=f"wk_{week}")
            elif status == "unlocked":
                clicked = st.button(f"{label} ✅", key=f"wk_{week}")
            else:
                clicked = False
                st.button(f"{label} 🔒", disabled=True, key=f"wk_{week}")

            if clicked and status in {"unlocked", "completed"}:
                st.session_state["selected_week"] = week

    st.divider()

    selected_week = st.session_state["selected_week"]

    if selected_week:
        st.header(f"📘 Week {selected_week}")

        md_path = os.path.join(CONTENT_DIR, f"week{selected_week}.md")
        if not os.path.exists(md_path):
            st.error("Week content not found. Please contact admin.")
            return

        with open(md_path, "r", encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)

        st.divider()
        st.subheader("📤 Assignment Submission")

        existing = get_assignment(user["id"], selected_week)

        if existing:
            st.success("✅ Assignment submitted.")
            st.write(f"**Status:** {existing['status']}")
            st.write(f"**Submitted at:** {existing['submitted_at']}")

            if existing.get("file_path") and os.path.exists(existing["file_path"]):
                with open(existing["file_path"], "rb") as fpdf:
                    st.download_button(
                        "⬇️ Download your submitted PDF",
                        data=fpdf,
                        file_name=existing.get("original_filename") or f"{user['username']}_week_{selected_week}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

            if existing["status"] in {"approved", "rejected"}:
                st.info("🧾 Review Result")
                if existing.get("grade") is not None:
                    st.write(f"**Grade:** {existing['grade']}%")
                if existing.get("feedback"):
                    st.write(f"**Feedback:** {existing['feedback']}")
                if existing.get("reviewed_at"):
                    st.write(f"**Reviewed at:** {existing['reviewed_at']}")
            else:
                st.warning("⏳ Pending admin review. Your grade will appear here after review.")

        else:
            uploaded_file = st.file_uploader(
                "Upload your assignment (PDF only)",
                type=["pdf"],
                key=f"upload_week_{selected_week}",
            )

            if uploaded_file and st.button("Submit Assignment", use_container_width=True):
                save_assignment(user["id"], selected_week, uploaded_file)

                # keep the user on the same selected week after rerun
                st.session_state["selected_week"] = selected_week
                st.success("🎉 Submitted successfully! (Pending admin review)")
                st.rerun()

    st.divider()
    st.subheader("📊 My Grades (All Weeks)")
    rows = list_student_assignments(user["id"])
    if rows:
        table = []
        for r in rows:
            table.append(
                {
                    "Week": r["week"],
                    "Status": r["status"],
                    "Grade (%)": "" if r.get("grade") is None else r["grade"],
                }
            )
        st.table(table)
    else:
        st.caption("No submissions yet.")

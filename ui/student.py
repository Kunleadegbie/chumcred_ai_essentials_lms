import os
import streamlit as st
from datetime import datetime

from services.db import read_conn, write_txn
from services.progress import (
    is_orientation_completed,
    mark_orientation_completed,
    mark_week_completed,
)
from services.assignments import (
    save_assignment,
    list_student_assignments,
)
from services.broadcasts import get_active_broadcasts

CONTENT_DIR = "content"


# =========================================================
# MAIN ROUTER
# =========================================================
def student_router(user):

    user_id = user["id"]
    username = user["username"]

    st.sidebar.title(f"👋 {username}")

    # =========================================================
    # ORIENTATION GATE (WEEK 0)
    # =========================================================
    if not is_orientation_completed(user_id):

        st.header("🧭 Orientation (Week 0)")

        md_path = os.path.join(CONTENT_DIR, "week0.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.warning("Orientation content not found.")

        if st.button("✅ I have read and understood the Orientation"):
            mark_orientation_completed(user_id)
            mark_week_completed(user_id, 1)
            st.success("Orientation completed. Week 1 unlocked.")
            st.rerun()

        st.stop()

    # =========================================================
    # SIDEBAR NAVIGATION
    # =========================================================
    menu = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Week 1",
            "Week 2",
            "Week 3",
            "Week 4",
            "Week 5",
            "Week 6",
            "Help & Support",
        ],
    )

    # =========================================================
    # DASHBOARD
    # =========================================================
    if menu == "Dashboard":

        st.header("📊 Student Dashboard")

        # -------------------------------
        # Broadcasts (Auto-expire handled in backend)
        # -------------------------------
        broadcasts = get_active_broadcasts()

        for b in broadcasts:
            st.info(b["message"])

        # -------------------------------
        # Assignment Summary
        # -------------------------------
        assignments = list_student_assignments(user_id)

        if assignments:
            st.subheader("📚 Assignment History")

            for a in assignments:
                st.markdown(f"**Week {a['week']}**")

                if a.get("grade") is not None:
                    st.success(f"Grade: {a['grade']}%")

                if a.get("feedback"):
                    st.info(f"Feedback: {a['feedback']}")

                st.divider()
        else:
            st.write("No assignments submitted yet.")

    # =========================================================
    # WEEK PAGES
    # =========================================================
    elif menu.startswith("Week"):

        week_number = int(menu.split(" ")[1])

        st.header(f"📘 {menu}")

        md_path = os.path.join(CONTENT_DIR, f"week{week_number}.md")

        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.warning("Week content not available.")

        # -------------------------------
        # Assignment Upload
        # -------------------------------
        st.subheader("📤 Submit Assignment")

        uploaded_file = st.file_uploader(
            "Upload your assignment (PDF only)",
            type=["pdf"],
            key=f"upload_week_{week_number}",
        )

        if uploaded_file:
            if st.button("Submit Assignment", key=f"submit_week_{week_number}"):

                save_assignment(
                    user_id=user_id,
                    week=week_number,
                    uploaded_file=uploaded_file,
                )

                st.success("Assignment submitted successfully.")
                st.rerun()

    # =========================================================
    # HELP & SUPPORT (PROPER PAGE)
    # =========================================================
    elif menu == "Help & Support":

        st.header("🆘 Help & Support")

        st.markdown(
            """
If you need assistance regarding:

- Assignment
- Technical issue
- Login problem
- Course clarification

Kindly submit your request below.
"""
        )

        subject = st.text_input("Subject")
        message = st.text_area("Describe your issue")

        if st.button("Submit Support Request"):

            if not subject or not message:
                st.error("Please complete all fields.")
            else:
                # Minimal implementation (safe for live system)
                with write_txn() as conn:
                    conn.execute(
                        """
                        INSERT INTO support_requests
                        (user_id, subject, message, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            subject,
                            message,
                            datetime.utcnow().isoformat(),
                        ),
                    )
                    conn.commit()

                st.success("✅ Your message has been sent. We will respond within 24 hours.")

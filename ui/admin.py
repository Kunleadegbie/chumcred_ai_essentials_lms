import os
import streamlit as st

from services.db import read_conn, write_txn
from services.auth import (
    create_user,
    get_all_students,
    reset_user_password,
)

from services.broadcasts import (
    create_broadcast,
    get_active_broadcasts,
    delete_broadcast,
)

from services.progress import (
    unlock_week_for_user,
    lock_week_for_user,
    mark_week_completed,
)

from services.assignments import (
    list_all_assignments,
    review_assignment,
)

CONTENT_DIR = "content"
TOTAL_WEEKS = 6


def admin_router(user):

    st.title("🛠 Admin Dashboard")
    st.caption(f"Welcome, {user['username']}")

    # ================= SIDEBAR =================
    with st.sidebar:

        st.markdown("### 🛠 Admin Menu")

        menu = st.radio(
            "Navigation",
            [
                "Dashboard",
                "Create Student",
                "All Students",
                "Individual Week Unlock",
                "Group Week Unlock",
                "Reset Password",
                "Assignment Review",
                "Broadcast Announcement",
                "Unlock Exam",
                "Student Reports",
                "Exam Analytics",
                "Help & Support",
                "Support Messages",
            ],
        )

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    # =========================================================
    # DASHBOARD
    # =========================================================
    if menu == "Dashboard":

        st.subheader("📢 Broadcasts")

        broadcasts = get_active_broadcasts()

        if broadcasts:
            for b in broadcasts:
                st.markdown(f"**{b['title']}**")
                st.write(b["message"])
                st.divider()
        else:
            st.info("No active broadcasts.")

    # =========================================================
    # CREATE STUDENT
    # =========================================================
    elif menu == "Create Student":

        st.subheader("➕ Create Student")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        cohort = st.text_input("Cohort", value="Cohort 1")

        if st.button("Create Student"):
            create_user(username, password, "student", cohort)
            st.success("Student created successfully.")

    # =========================================================
    # ALL STUDENTS
    # =========================================================
    elif menu == "All Students":

        st.subheader("👥 All Students")

        students = get_all_students()

        if students:
            st.dataframe(students, use_container_width=True)
        else:
            st.info("No students found.")

    # =========================================================
    # UNLOCK EXAM
    # =========================================================
    elif menu == "Unlock Exam":

        st.subheader("📝 Unlock Final Exam")

        with read_conn() as conn:
            rows = conn.execute(
                "SELECT id,username FROM users WHERE role='student'"
            ).fetchall()

        students = {r["username"]: r["id"] for r in rows}

        selected = st.selectbox("Student", list(students.keys()))

        if st.button("Unlock Exam"):

            uid = students[selected]

            with write_txn() as conn:

                conn.execute(
                    """
                    INSERT OR IGNORE INTO student_exam_status(user_id,exam_unlocked)
                    VALUES (?,1)
                    """,
                    (uid,),
                )

                conn.execute(
                    """
                    UPDATE student_exam_status
                    SET exam_unlocked=1
                    WHERE user_id=?
                    """,
                    (uid,),
                )

            st.success("Exam unlocked")

    # =========================================================
    # STUDENT REPORTS
    # =========================================================
    elif menu == "Student Reports":

        st.subheader("📊 Student Exam Scores")

        with read_conn() as conn:

            rows = conn.execute(
                """
                SELECT u.username,
                       s.last_score,
                       s.attempts
                FROM student_exam_status s
                JOIN users u
                ON s.user_id=u.id
                """
            ).fetchall()

        if rows:
            st.dataframe([dict(r) for r in rows])
        else:
            st.info("No exam data yet.")

    # =========================================================
    # EXAM ANALYTICS
    # =========================================================
    elif menu == "Exam Analytics":

        st.subheader("📈 Exam Analytics")

        with read_conn() as conn:

            data = conn.execute(
                """
                SELECT
                AVG(last_score) avg_score,
                MAX(last_score) max_score,
                MIN(last_score) min_score
                FROM student_exam_status
                """
            ).fetchone()

        if data:

            st.metric("Average Score", round(data["avg_score"] or 0,2))
            st.metric("Highest Score", data["max_score"])
            st.metric("Lowest Score", data["min_score"])

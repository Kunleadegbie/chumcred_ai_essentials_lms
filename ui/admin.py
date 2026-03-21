import os
import streamlit as st

from services.db import read_conn, write_txn
from services.auth import create_user, get_all_students, reset_user_password
from services.broadcasts import create_broadcast, get_active_broadcasts, delete_broadcast
from services.progress import unlock_week_for_user, lock_week_for_user, mark_week_completed
from services.assignments import list_all_assignments, review_assignment

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
            st.info("No broadcasts yet.")

        # ✅ RESTORED: Weekly content preview (Week 1–6)
        st.divider()
        st.subheader("📚 Weekly Content (Weeks 1–6)")

        for wk in range(1, TOTAL_WEEKS + 1):
            md_path = os.path.join(CONTENT_DIR, f"week{wk}.md")
            with st.expander(f"Week {wk} Content", expanded=False):
                if os.path.exists(md_path):
                    with open(md_path, "r", encoding="utf-8") as f:
                        st.markdown(f.read())
                else:
                    st.warning(f"Content file not found: {md_path}")

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
    # INDIVIDUAL WEEK UNLOCK
    # =========================================================
    elif menu == "Individual Week Unlock":

        st.subheader("🔓 Unlock Week for Student")

        with read_conn() as conn:
            rows = conn.execute(
                "SELECT id,username FROM users WHERE role='student'"
            ).fetchall()

        students = {r["username"]: r["id"] for r in rows}

        selected = st.selectbox("Select Student", list(students.keys()))

        week = st.number_input(
            "Week",
            min_value=1,
            max_value=TOTAL_WEEKS,
            step=1,
        )

        if st.button("Unlock Week"):

            mark_week_completed(students[selected], week)

            st.success(f"Week {week} unlocked for {selected}")

    # =========================================================
    # GROUP WEEK UNLOCK
    # =========================================================
    elif menu == "Group Week Unlock":

        st.subheader("🔓 Group Week Unlock")

        students = get_all_students()

        week = st.selectbox(
            "Week",
            list(range(1, TOTAL_WEEKS + 1)),
        )

        action = st.radio(
            "Action",
            ["Unlock Week", "Lock Week"],
        )

        if st.button("Apply"):

            for s in students:

                sid = s["id"] if isinstance(s, dict) else s[0]

                if action == "Unlock Week":
                    unlock_week_for_user(sid, week)
                else:
                    lock_week_for_user(sid, week)

            st.success("Update completed.")

    # =========================================================
    # RESET PASSWORD
    # =========================================================
    elif menu == "Reset Password":

        st.subheader("🔐 Reset Password")

        with read_conn() as conn:
            rows = conn.execute(
                "SELECT username FROM users WHERE role='student'"
            ).fetchall()

        students = [r["username"] for r in rows]

        selected = st.selectbox("Student", students)

        new_password = st.text_input("New Password", type="password")

        if st.button("Reset Password"):
            reset_user_password(selected, new_password)
            st.success("Password reset successfully.")

    # =========================================================
    # ASSIGNMENT REVIEW
    # =========================================================
    elif menu == "Assignment Review":

        st.subheader("📤 Assignment Review")

        assignments = list_all_assignments()

        if not assignments:
            st.info("No submissions yet.")
            return

        for a in assignments:

            a = dict(a)

            st.markdown(f"**Student:** {a.get('username','—')}  ")
            st.markdown(f"**Week:** {a.get('week','—')}")

            # ✅ show the uploaded assignment file to admin (download/open)
            file_path = a.get("file_path") or a.get("path")
            file_name = (
                a.get("original_filename")
                or a.get("filename")
                or a.get("file_name")
                or "assignment_file"
            )

            if file_path:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        st.download_button(
                            "⬇️ Download Assignment File",
                            data=f.read(),
                            file_name=file_name,
                            mime="application/octet-stream",
                            key=f"dl_{a.get('id')}_{a.get('week')}",
                        )
                else:
                    st.warning("⚠️ Assignment file path saved, but file not found on server.")
                    st.code(str(file_path))
            else:
                st.warning("⚠️ No file path found in this submission record (file_path/path is empty).")

            grade = st.number_input(
                "Grade",
                min_value=0.0,
                max_value=100.0,
                value=float(a.get("grade") or 0),
                key=f"grade_{a['id']}",
            )

            feedback = st.text_area(
                "Feedback",
                value=a.get("feedback") or "",
                key=f"fb_{a['id']}",
            )

            if st.button("Submit Review", key=f"review_{a['id']}"):
                review_assignment(a["id"], grade, feedback)
                st.success("Assignment graded.")
                st.rerun()

            st.divider()

    # =========================================================
    # BROADCAST
    # =========================================================
    elif menu == "Broadcast Announcement":

        st.subheader("📢 Broadcast")

        title = st.text_input("Title")
        message = st.text_area("Message")

        if st.button("Post Broadcast"):
            create_broadcast(title, message, user["id"])
            st.success("Broadcast posted.")

        st.divider()

        for b in get_active_broadcasts():
            st.markdown(f"**{b['title']}**")
            st.write(b["message"])

            if st.button("Delete", key=f"del_{b['id']}"):
                delete_broadcast(b["id"])
                st.rerun()

    # =========================================================
    # UNLOCK EXAM
    # =========================================================
    elif menu == "Unlock Exam":

        st.subheader("📝 Unlock Final Exam")

        with read_conn() as conn:
            rows = conn.execute(
                "SELECT id, username FROM users WHERE role='student'"
            ).fetchall()

        students = {f"{r['username']} (ID {r['id']})": r["id"] for r in rows}

        selected = st.selectbox("Select Student", list(students.keys()))

        if st.button("Unlock Exam"):

            student_id = students[selected]

            with write_txn() as conn:

                conn.execute(
                    """
                    INSERT OR IGNORE INTO student_exam_status (user_id, exam_unlocked)
                    VALUES (?,1)
                    """,
                    (student_id,)
                )

                conn.execute(
                    """
                    UPDATE student_exam_status
                    SET exam_unlocked = 1
                    WHERE user_id = ?
                    """,
                    (student_id,)
                )

            st.success(f"Exam unlocked for {selected}")

    # =========================================================
    # STUDENT REPORTS
    # =========================================================
    elif menu == "Student Reports":

        st.subheader("📊 Student Exam Scores")

        with read_conn() as conn:

            rows = conn.execute(
                """
                SELECT u.username,s.last_score,s.attempts
                FROM student_exam_status s
                JOIN users u ON s.user_id=u.id
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

            st.metric("Average Score", round(data["avg_score"] or 0, 2))
            st.metric("Highest Score", data["max_score"])
            st.metric("Lowest Score", data["min_score"])

    # =========================================================
    # HELP
    # =========================================================
    elif menu == "Help & Support":

        from ui.admin_support import admin_support_page
        admin_support_page(user)

    # =========================================================
    # SUPPORT MESSAGES
    # =========================================================
    elif menu == "Support Messages":

        st.subheader("🆘 Student Support Messages")

        with read_conn() as conn:
            rows = conn.execute(
                """
                SELECT sm.subject,sm.message,u.username
                FROM support_messages sm
                JOIN users u ON sm.user_id=u.id
                ORDER BY sm.created_at DESC
                """
            ).fetchall()

        if rows:

            for r in rows:
                st.markdown(f"**{r['username']}**")
                st.markdown(f"**Subject:** {r['subject']}")
                st.info(r["message"])
                st.divider()

        else:
            st.info("No support messages.")
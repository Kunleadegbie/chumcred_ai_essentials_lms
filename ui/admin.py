# ui/admin.py

import os
import streamlit as st
from services.db import read_conn

from services.auth import (
    create_user,
    get_all_students,
    reset_user_password,
    list_all_users,  # kept (even if not used elsewhere)
)

from services.broadcasts import (
    create_broadcast,
    get_active_broadcasts,
    delete_broadcast,
)
from services.auth import list_all_users, reset_user_password


from services.progress import (
    unlock_week_for_user,
    lock_week_for_user,
)

from services.assignments import (
    list_all_assignments,
    review_assignment,
)

from services.broadcasts import (
    create_broadcast,
    get_active_broadcasts,
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
                "Reset Password",
                "Group Week Unlock",
                "Assignment Review",
                "Broadcast Announcement",
                "Help & Support",
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

        st.subheader("📘 Course Content (Admin View)")

        for week in range(0, TOTAL_WEEKS + 1):
            label = "Orientation (Week 0)" if week == 0 else f"Week {week}"
            md_path = os.path.join(CONTENT_DIR, f"week{week}.md")

            with st.expander(label):
                if os.path.exists(md_path):
                    with open(md_path, encoding="utf-8") as f:
                        st.markdown(f.read(), unsafe_allow_html=True)
                else:
                    st.warning("Content file not found.")

    # =========================================================
    # CREATE STUDENT
    # =========================================================
    elif menu == "Create Student":
        st.subheader("➕ Create Student")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        cohort = st.text_input("Cohort", value="Cohort 1")

        if st.button("Create Student"):
            try:
                create_user(
                    username=username,
                    password=password,
                    role="student",
                    cohort=cohort,
                )
                st.success("Student created successfully.")
            except Exception as e:
                st.error(str(e))

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
    # INDIVIDUAL STUDENT UNLOCK
    # =========================================================

    st.subheader("🔓 Unlock Week for Individual Student")

    students = {
        f"{u['username']} (ID {u['id']})": u["id"]
        for u in users
        if u.get("role") == "student"
    }

    if students:
        selected_student = st.selectbox(
            "Select Student",
            options=list(students.keys())
        )

    week_to_unlock = st.number_input(
        "Week to Unlock",
        min_value=1,
        max_value=12,
        step=1
    )

    if st.button("Unlock Selected Week"):
        student_id = students[selected_student]

        mark_week_completed(student_id, week_to_unlock)

        st.success(
            f"✅ Week {week_to_unlock} unlocked for {selected_student}"
        )
    else:
        st.info("No students found.")


    # =========================================================
    # RESET PASSWORD
    # =========================================================
    if menu == "Reset Password":
        st.subheader("🔐 Reset Student Password")

        # Load students from DB (authoritative)
        with read_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, username
                FROM users
                WHERE role = 'student'
                ORDER BY username
                """
            ).fetchall()

       students = [dict(r) for r in rows]

       if not students:
           st.warning("No students found.")
           st.stop()

       # Map username -> id
       student_map = {s["username"]: s["id"] for s in students}

       selected_student = st.selectbox(
           "Select Student",
           list(student_map.keys()),
           key="reset_pw_student_select"
       )

       new_password = st.text_input("New Password", type="password")
       confirm_password = st.text_input("Confirm Password", type="password")

       if st.button("🔄 Reset Password", key="admin_reset_pw_btn"):
           if not new_password:
               st.error("Please enter a password.")
       elif new_password != confirm_password:
           st.error("Passwords do not match.")
       elif len(new_password) < 6:
           st.error("Password must be at least 6 characters.")
       else:
           # Username-based reset (authoritative & safe)
           reset_user_password(selected_student, new_password)

           st.success(f"✅ Password reset successfully for: {selected_student}")
           st.session_state["pw_reset_done"] = True
    

    # =========================================================
    # GROUP WEEK UNLOCK
    # =========================================================
    elif menu == "Group Week Unlock":
        st.subheader("🔓 Group Week Unlock")

        students = get_all_students()

        if not students:
            st.info("No students available.")
            return

        selected_week = st.selectbox(
            "Select Week",
            options=list(range(1, TOTAL_WEEKS + 1)),
        )

        action = st.radio("Action", ["Unlock Week", "Lock Week"])

        if st.button("Apply to ALL Students"):
            for s in students:
                # s may be sqlite Row/dict; support both safely
                sid = s["id"] if isinstance(s, dict) else s[0]
                if action == "Unlock Week":
                    unlock_week_for_user(sid, selected_week)
                else:
                    lock_week_for_user(sid, selected_week)

            st.success(f"Week {selected_week} updated for all students.")

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
            # If a is sqlite Row, dict(a) makes it safe everywhere
            if not isinstance(a, dict):
                a = dict(a)

            st.markdown(
                f"""
**Student:** {a['username']}  
**Week:** {a['week']}  
**Submitted:** {a['submitted_at']}
"""
            )

            # ================= DOWNLOAD =================
            file_path = a.get("file_path")

            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    file_bytes = f.read()

                st.download_button(
                    label="⬇️ Download Assignment",
                    data=file_bytes,
                    file_name=os.path.basename(file_path),
                    mime="application/octet-stream",
                    key=f"dl_{a['id']}",
                )
            else:
                st.error("❌ File not found on server")

            # ================= GRADING =================
            grade_val = a.get("grade")
            grade_float = float(grade_val) if grade_val is not None else 0.0

            grade = st.number_input(
                "Grade (%)",
                min_value=0.0,
                max_value=100.0,
                value=grade_float,
                step=1.0,
                key=f"grade_{a['id']}",
            )

            feedback = st.text_area(
                "Feedback",
                value=a["feedback"] if a.get("feedback") else "",
                key=f"fb_{a['id']}",
            )

            if st.button("✅ Submit Review", key=f"review_{a['id']}"):
                review_assignment(
                    assignment_id=a["id"],
                    grade=grade,
                    feedback=feedback,
                )
                st.success("Assignment graded successfully.")
                st.rerun()

            st.divider()

    # =================================================
    # BROADCAST MANAGEMENT
    # =================================================
    elif menu == "Broadcast Announcement":

        st.subheader("📢 Post Broadcast")

        if not st.session_state.get("broadcast_posted"):
            title = st.text_input("Title")
            message = st.text_area("Message")

            if st.button("Post Broadcast"):
                if not title or not message:
                    st.error("Title and message required.")
                else:
                    create_broadcast(title, message, user["id"])
                    st.success("✅ Broadcast posted successfully.")
                    st.session_state["broadcast_posted"] = True
                    st.rerun()
        else:
            st.info("Broadcast already posted. Reload page to post another.")

        st.divider()
        st.subheader("📋 Active Broadcasts")

        broadcasts = get_active_broadcasts()
        for b in broadcasts:
            st.markdown(f"**{b['title']}**\n\n{b['message']}")
            if st.button("🗑 Delete", key=f"del_{b['id']}"):
                delete_broadcast(b["id"])
                st.success("Broadcast deleted.")
                st.rerun()


    # =========================================================
    # HELP
    # =========================================================
    elif menu == "Help & Support":
        from ui.help import help_router

        help_router(user, role="admin")

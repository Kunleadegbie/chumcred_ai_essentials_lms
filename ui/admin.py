

# ui/admin.py 
# new additions
# ui/admin.py
import streamlit as st
from datetime import datetime

from services.db import read_conn, write_txn
from services.progress import unlock_week_for_user
from services.assignments import list_all_assignments, review_assignment
from services.broadcasts import create_broadcast
from services.auth import create_user, get_all_students


def admin_router(user):
    st.title("🛠 Admin Dashboard")
    st.caption(f"Welcome, {user['username']}")

    menu = st.sidebar.radio(
        "Admin Menu",
        [
            "Dashboard",
            "Create Student",
            "All Students",
            "Assignment Review",
            "Week Control",
        ]
    )

    if menu == "Dashboard":
        _dashboard(user)

    elif menu == "Create Student":
        _create_student()

    elif menu == "All Students":
        _all_students()

    elif menu == "Assignment Review":
        _assignment_review()

    elif menu == "Week Control":
        _week_control()


def _dashboard(admin_user):
    st.subheader("📢 Send Broadcast Message")

    with st.form("broadcast_form"):
        title = st.text_input("Title")
        message = st.text_area("Message")
        send = st.form_submit_button("Send Broadcast")

    if send:
        if not title or not message:
            st.error("Title and message required.")
        else:
            create_broadcast(title, message, admin_user["id"])
            st.success("Broadcast sent.")
            st.rerun()


def _create_student():
    st.subheader("➕ Create Student")

    with st.form("create_student"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        cohort = st.text_input("Cohort", value="Cohort 1")
        submit = st.form_submit_button("Create Student")

    if submit:
        if not username or not password:
            st.error("Username and password required.")
            return
        try:
            create_user(username=username, password=password, cohort=cohort)
            st.success("Student created.")
        except Exception as e:
            st.error(str(e))


def _all_students():
    st.subheader("👥 All Students")
    students = get_all_students()

    if not students:
        st.info("No students found.")
        return

    st.dataframe(students)


def _assignment_review():
    st.subheader("📤 Assignment Review")

    rows = list_all_assignments()
    if not rows:
        st.info("No assignments submitted yet.")
        return

    for r in rows:
        st.markdown(f"""
**Student:** {r['username']}  
**Week:** {r['week']}  
**Submitted:** {r['submitted_at']}
""")

        grade = st.number_input(
            f"Grade (Week {r['week']} — {r['username']})",
            min_value=0,
            max_value=100,
            key=f"grade_{r['id']}"
        )

        feedback = st.text_area(
            "Feedback",
            key=f"feedback_{r['id']}"
        )

        if st.button("Approve & Grade", key=f"approve_{r['id']}"):
            review_assignment(
                assignment_id=r["id"],
                grade=grade,
                feedback=feedback
            )
            st.success("Assignment graded.")
            st.rerun()

        st.divider()


def _week_control():
    st.subheader("🔓 Unlock Weeks for Students")

    students = get_all_students()
    if not students:
        st.info("No students available.")
        return

    student = st.selectbox("Select Student", students, format_func=lambda x: x["username"])
    week = st.selectbox("Select Week", [1, 2, 3, 4, 5, 6])

    if st.button("Unlock Week"):
        unlock_week_for_user(student["id"], week)
        st.success(f"Week {week} unlocked for {student['username']}.")

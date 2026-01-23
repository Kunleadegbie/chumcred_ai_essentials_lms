

# ui/admin.py 
# ui/admin.py


import os

import streamlit as st
from datetime import datetime

from services.progress import unlock_week_for_user
from services.assignments import list_all_assignments, review_assignment
from services.broadcasts import create_broadcast
from services.auth import create_user, get_all_students


def admin_router(user):
    st.title("🛠 Admin Dashboard")
    st.caption(f"Welcome, {user['username']}")

    # ---------------- SIDEBAR ----------------
    with st.sidebar:
        st.markdown("### 🛠 Admin Menu")

        menu = st.radio(
            "Navigate",
            [
                "Dashboard",
                "Create Student",
                "All Students",
                "Assignment Review",
                "Week Control",
                "Help & Support",
            ],
        )

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()



    menu = st.radio(
    "Admin Menu",
    [
        "Dashboard",
        "Broadcast",
        "Group Week Unlock",   # 🔴 THIS MUST RETURN
        "Individual Week Control",
        "Assignments Review",
        "All Students",
        "Help & Support",
    ]
  )


    # ---------------- ROUTING ----------------
    if menu == "Dashboard":
        dashboard_view(user)

    elif menu == "Create Student":
        create_student_view()

    elif menu == "All Students":
        all_students_view()

    elif menu == "Assignment Review":
        assignment_review_view()

    elif menu == "Week Control":
        week_control_view()

    elif menu == "Help & Support":
        from ui.help import help_router
        help_router(user, role="admin")


# ---------------- DASHBOARD ----------------
def dashboard_view(admin_user):
    st.subheader("📢 Broadcast Announcement")

    with st.form("broadcast_form"):
        title = st.text_input("Title")
        message = st.text_area("Message")
        send = st.form_submit_button("Send Broadcast")

    if send:
        if not title or not message:
            st.error("Title and message required.")
        else:
            create_broadcast(title, message, admin_user["id"])
            st.success("Broadcast sent to all students.")
            st.rerun()

st.divider()
st.subheader("📘 Course Content Preview (Admin Only)")

CONTENT_DIR = "content"
weeks = [0, 1, 2, 3, 4, 5, 6]

selected_week = st.selectbox(
    "Select week to preview",
    weeks,
    format_func=lambda w: "Orientation (Week 0)" if w == 0 else f"Week {w}"
)

md_path = os.path.join(CONTENT_DIR, f"week{selected_week}.md")

if os.path.exists(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)
else:
    st.warning("Content file not found.")



# ===============================
# COURSE CONTENT (ADMIN VIEW)
# ===============================
st.divider()
st.subheader("📘 Course Content Preview (Admin Only)")
st.caption("Read-only preview of Week 1–6 learning materials.")

CONTENT_DIR = "content"
TOTAL_WEEKS = 6

selected_week = st.selectbox(
    "Select a week to preview",
    options=list(range(1, TOTAL_WEEKS + 1)),
    format_func=lambda w: f"Week {w}"
)

md_path = os.path.join(CONTENT_DIR, f"week{selected_week}.md")

if not os.path.exists(md_path):
    st.error(f"Content file for Week {selected_week} not found.")
else:
    with open(md_path, encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)



# ---------------- CREATE STUDENT ----------------
def create_student_view():
    st.subheader("➕ Create Student")

    with st.form("create_student_form"):
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
            st.success("Student created successfully.")
        except Exception as e:
            st.error(str(e))


# ---------------- ALL STUDENTS ----------------
def all_students_view():
    st.subheader("👥 All Students")

    students = get_all_students()
    if not students:
        st.info("No students found.")
        return

    st.dataframe(students, use_container_width=True)


# ---------------- ASSIGNMENT REVIEW ----------------
def assignment_review_view():
    st.subheader("📤 Assignment Review")

    rows = list_all_assignments()
    if not rows:
        st.info("No assignments submitted yet.")
        return

    for r in rows:
        st.markdown(
            f"""
**Student:** {r['username']}  
**Week:** {r['week']}  
**Submitted:** {r['submitted_at']}
"""
        )

        grade = st.number_input(
            "Grade",
            min_value=0,
            max_value=100,
            key=f"grade_{r['id']}",
        )

        feedback = st.text_area(
            "Feedback",
            key=f"feedback_{r['id']}",
        )

        if st.button("Approve & Grade", key=f"approve_{r['id']}"):
            review_assignment(
                assignment_id=r["id"],
                grade=grade,
                feedback=feedback,
            )
            st.success("Assignment graded.")
            st.rerun()

        st.divider()


# ---------------- WEEK CONTROL ----------------
def week_control_view():
    st.subheader("🔓 Unlock Weeks")

    students = get_all_students()
    if not students:
        st.info("No students available.")
        return

    student = st.selectbox(
        "Select Student",
        students,
        format_func=lambda x: x["username"],
    )

    week = st.selectbox("Select Week", [1, 2, 3, 4, 5, 6])

    if st.button("Unlock Week"):
        unlock_week_for_user(student["id"], week)
        st.success(f"Week {week} unlocked for {student['username']}.")


elif menu == "Group Week Unlock":
    st.subheader("🔓 Group Week Unlock (By Cohort)")

    cohort = st.selectbox("Select Cohort", get_all_cohorts())
    week = st.selectbox("Week to Unlock", [1, 2, 3, 4, 5, 6])

    if st.button("Unlock Week for Cohort"):
        unlock_week_for_cohort(cohort, week)
        st.success(f"Week {week} unlocked for {cohort}")


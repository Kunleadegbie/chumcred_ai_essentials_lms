

# ui/admin.py 
# ui/admin.py

import os
import streamlit as st


from services.db import DB_PATH

st.info("🔍 DATABASE DEBUG")
st.write("DB_PATH from code:", DB_PATH)
st.write("LMS_DB_PATH env:", os.getenv("LMS_DB_PATH"))


from services.auth import (
    create_user,
    get_all_students,
)
from services.progress import (
    unlock_week_for_user,
    lock_week_for_user,
    get_progress,
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

    # ---------------- SIDEBAR ----------------
    with st.sidebar:
        st.markdown("### 🛠 Admin Menu")

        menu = st.radio(
            "Navigation",
            [
                "Dashboard",
                "Create Student",
                "All Students",
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
    # GROUP WEEK UNLOCK  ✅ (FIXED)
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

        action = st.radio(
            "Action",
            ["Unlock Week", "Lock Week"],
        )

        if st.button("Apply to ALL Students"):
            for s in students:
                if action == "Unlock Week":
                    unlock_week_for_user(s["id"], selected_week)
                else:
                    lock_week_for_user(s["id"], selected_week)

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
        st.markdown(
            f"""
**Student:** {a['username']}  
**Week:** {a['week']}  
**Submitted:** {a['submitted_at']}
"""
        )

        st.link_button("📄 Download", a["file_path"])

        grade = st.number_input(
            "Grade (%)",
            min_value=0,
            max_value=100,
            value=a.get("grade") or 0,
            key=f"grade_{a['id']}",
        )

        feedback = st.text_area(
            "Feedback",
            value=a.get("feedback") or "",
            key=f"fb_{a['id']}",
        )

        if st.button("✅ Submit Review", key=f"review_{a['id']}"):

            review_assignment(
                assignment_id=a["id"],
                grade=grade,
                feedback=feedback,
                status="graded",     # ✅ VERY IMPORTANT
            )

            st.success("Assignment graded successfully.")
            st.rerun()

        st.divider()



    
    # =========================================================
    # BROADCAST
    # =========================================================
    elif menu == "Broadcast Announcement":
        st.subheader("📢 Create Broadcast")

        title = st.text_input("Title")
        message = st.text_area("Message")

        if st.button("Send Broadcast"):
            create_broadcast(title, message, user["id"])
            st.success("Broadcast sent.")
            st.rerun()

    # =========================================================
    # HELP & SUPPORT
    # =========================================================
    elif menu == "Help & Support":
        from ui.help import help_router
        help_router(user, role="admin")

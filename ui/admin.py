# ui/admin.py

import os
import streamlit as st
from services.db import read_conn, DB_PATH


from services.auth import (
    create_user,
    get_all_students,
    reset_user_password,
    list_all_users,
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
    # INDIVIDUAL WEEK UNLOCK (RESTORED)
    # =========================================================
    elif menu == "Individual Week Unlock":
        st.subheader("🔓 Unlock Week for Individual Student")

        with read_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, username
                FROM users
                WHERE role = 'student'
                ORDER BY username
                """
        ).fetchall()

        students = {
            f"{r['username']} (ID {r['id']})": r["id"]
            for r in rows
        }


        if not students:
            st.info("No students found.")
            return

        selected_student = st.selectbox(
            "Select Student",
            options=list(students.keys())
        )

        week_to_unlock = st.number_input(
            "Week to Unlock",
            min_value=1,
            max_value=TOTAL_WEEKS,
            step=1
        )

        if st.button("Unlock Selected Week"):
            student_id = students[selected_student]
            mark_week_completed(student_id, week_to_unlock)

            st.success(
                f"✅ Week {week_to_unlock} unlocked for {selected_student}"
            )

    # =========================================================
    # RESET PASSWORD (FIXED)
    # =========================================================
    elif menu == "Reset Password":
        st.subheader("🔐 Reset Student Password")

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
                reset_user_password(selected_student, new_password)
                st.success(f"✅ Password reset successfully for: {selected_student}")

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
            if not isinstance(a, dict):
                a = dict(a)

            st.markdown(
                f"""
**Student:** {a['username']}  
**Week:** {a['week']}  
**Submitted:** {a['submitted_at']}
"""
            )

            file_path = a.get("file_path")
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download Assignment",
                        f.read(),
                        file_name=os.path.basename(file_path),
                        key=f"dl_{a['id']}",
                    )
            else:
                st.error("❌ File not found on server")

            grade = st.number_input(
                "Grade (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(a.get("grade") or 0),
                step=1.0,
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
                )
                st.success("Assignment graded successfully.")
                st.rerun()

            st.divider()

    # =========================================================
    # BROADCAST MANAGEMENT
    # =========================================================
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

        for b in get_active_broadcasts():
            st.markdown(f"**{b['title']}**\n\n{b['message']}")
            if st.button("🗑 Delete", key=f"del_{b['id']}"):
                delete_broadcast(b["id"])
                st.success("Broadcast deleted.")
                st.rerun()



    # =========================================================
    # HELP & SUPPORT (TICKETS)
    # =========================================================
    elif menu == "Help & Support":
        st.subheader("🆘 Help & Support (Student Enquiries)")

        # Show which DB file is in use (helps catch DB-path mismatch fast)
        try:
            st.caption(f"DB_PATH: {DB_PATH}")
        except Exception:
            pass

        rows = []
        ticket_cols = []
        with read_conn() as conn:
            # show SQLite file path
            try:
                db_row = conn.execute("PRAGMA database_list").fetchone()
                st.caption(f"SQLite file in use: {db_row[2] if db_row else 'unknown'}")
            except Exception:
                st.caption("SQLite file in use: (unable to read)")

            # discover ticket schema safely
            try:
                ticket_cols = [r[1] for r in conn.execute("PRAGMA table_info(support_tickets)").fetchall()]
            except Exception:
                ticket_cols = []

            if not ticket_cols:
                st.error("support_tickets table not found (or has no columns).")
                rows = []
            else:
                has_created_at = "created_at" in ticket_cols
                order_clause = "datetime(created_at) DESC" if has_created_at else "id DESC"

                # Select * so we never break on missing columns (e.g., student_username)
                rows = conn.execute(f"""
                    SELECT *
                    FROM support_tickets
                    ORDER BY {order_clause}
                    LIMIT 200
                """).fetchall()

        tickets = [dict(r) for r in rows] if rows else []

        if not tickets:
            st.info("No support tickets yet.")
        else:
            st.write(f"Tickets found: **{len(tickets)}**")

            for t in tickets:
                # Choose the best available student label
                student_label = (
                    t.get("student_username")
                    or t.get("student_name")
                    or t.get("username")
                    or str(t.get("student_user_id") or t.get("user_id") or "")
                )

                title = f"#{t.get('id')} • {student_label} • {t.get('status','open')}"
                with st.expander(title):
                    # Common fields (fallbacks included)
                    subject = t.get("subject") or ""
                    message = t.get("message") or t.get("body") or ""

                    if subject:
                        st.markdown(f"**Subject:** {subject}")
                    st.markdown("**Student message:**")
                    st.info(message)

                    if t.get("created_at"):
                        st.caption(f"Submitted: {t.get('created_at')}")
                    if t.get("replied_at"):
                        st.caption(f"Last replied: {t.get('replied_at')}")

                    # Admin actions (update only columns that exist)
                    status_options = ["open", "in_progress", "resolved", "closed"]
                    current_status = t.get("status", "open")
                    if current_status not in status_options:
                        current_status = "open"

                    new_status = st.selectbox(
                        "Status",
                        options=status_options,
                        index=status_options.index(current_status),
                        key=f"ticket_status_{t.get('id')}",
                    )

                    reply = st.text_area(
                        "Admin reply",
                        value=t.get("admin_reply") or "",
                        height=120,
                        key=f"ticket_reply_{t.get('id')}",
                    )

                    col_a, col_b = st.columns([1, 1])

                    with col_a:
                        if st.button("💾 Save update", key=f"save_ticket_{t.get('id')}"):
                            set_parts = []
                            params = []

                            if "status" in ticket_cols:
                                set_parts.append("status = ?")
                                params.append(new_status)

                            if "admin_reply" in ticket_cols:
                                set_parts.append("admin_reply = ?")
                                params.append(reply.strip() if reply else None)

                            if "replied_at" in ticket_cols:
                                set_parts.append("replied_at = datetime('now')")

                            if "replied_by" in ticket_cols:
                                set_parts.append("replied_by = ?")
                                params.append(user.get("id"))

                            if not set_parts:
                                st.warning("No updatable columns found on support_tickets.")
                            else:
                                sql = f"UPDATE support_tickets SET {', '.join(set_parts)} WHERE id = ?"
                                params.append(t.get("id"))
                                with read_conn() as conn:
                                    conn.execute(sql, params)
                                    try:
                                        conn.commit()
                                    except Exception:
                                        pass
                                st.success("Updated.")
                                st.rerun()

                    with col_b:
                        if st.button("🧹 Clear reply box", key=f"clear_reply_{t.get('id')}"):
                            st.session_state[f"ticket_reply_{t.get('id')}"] = ""
                            st.rerun()



    # =========================================================
    # SUPPORT MESSAGES
    # =========================================================
    elif menu == "Support Messages":

        st.subheader("🆘 Student Support Messages")

        with read_conn() as conn:
            rows = conn.execute("""
                SELECT sm.id,
                       u.username,
                       sm.subject,
                       sm.message,                       
                       sm.created_at
                FROM support_messages sm
                LEFT JOIN users u ON sm.user_id = u.id
                ORDER BY sm.created_at DESC
            """).fetchall()

        messages = [dict(r) for r in rows]

        if not rows:
            st.info("No support messages yet.")
        else:
            for r in rows:
                data = dict(r)

                st.markdown("### 📩 Support Request")
                st.markdown(f"**Student:** {data['username']}")
                st.markdown(f"**Subject:** {data['subject']}")
                st.markdown(f"**Message:**")
                st.info(data['message'])
                st.caption(f"Submitted: {data['created_at']}")
                st.divider()

            if msg["status"] == "open":
                if st.button("Mark as Resolved", key=f"resolve_{msg['id']}"):
                    with write_txn() as conn2:
                        conn2.execute("""
                            UPDATE support_messages
                            SET status = 'resolved'
                            WHERE id = ?
                        """, (msg["id"],))
                        conn2.commit()

                    st.success("Marked as resolved.")
                    st.rerun()
                else:
                    st.success("✅ Resolved")




    # =========================================================
    # HELP
    # =========================================================

    
    

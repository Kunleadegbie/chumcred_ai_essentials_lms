# --------------------------------------------------
# ui/admin.py
# --------------------------------------------------
import streamlit as st
from services.broadcasts import (
    create_broadcast,
    get_active_broadcasts,
    delete_broadcast,
)
from services.auth import list_all_users, reset_user_password


def admin_router(user):
    st.title("🛠 Admin Dashboard")

    menu = st.selectbox(
        "Admin Menu",
        ["Broadcast", "Reset Password"],
    )

    # =================================================
    # BROADCAST MANAGEMENT
    # =================================================
    if menu == "Broadcast":

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

    # =================================================
    # RESET STUDENT PASSWORD
    # =================================================
    elif menu == "Reset Password":

        st.subheader("🔐 Reset Student Password")

        users = list_all_users()
        students = {u["username"]: u["id"] for u in users if u["role"] == "student"}

        if not students:
            st.warning("No students found.")
            return

        student_name = st.selectbox("Select Student", students.keys())
        new_password = st.text_input("New Password", type="password")

        if st.button("Reset Password"):
            if not new_password:
                st.error("Password cannot be empty.")
            else:
                reset_user_password(students[student_name], new_password)
                st.success("✅ Password reset successfully.")

import streamlit as st
from services.db import write_txn
from datetime import datetime


def support_page(user):

    st.title("🆘 Help & Support")

    st.markdown(f"**Logged in as:** {user['username']}")

    st.markdown("""
If you have any questions, challenges, or technical issues,
please send a message to the facilitator below.
    """)

    subject = st.text_input("Subject")
    message = st.text_area("Your Message")

    if st.button("📩 Submit Request", key="submit_support_btn"):

        if not subject.strip() or not message.strip():
            st.error("Please complete all fields.")
            return

        with write_txn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO support_messages
                (user_id, subject, message, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                user["id"],
                subject.strip(),
                message.strip(),
                datetime.utcnow().isoformat()
            ))
            conn.commit()

        st.success("✅ Your message has been submitted successfully.")
        st.rerun()

    if st.button("⬅ Back to Dashboard"):
        st.session_state["page"] = "dashboard"
        st.rerun()

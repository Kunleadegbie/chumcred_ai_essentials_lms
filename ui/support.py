import streamlit as st
from datetime import datetime
from services.db import write_txn

def support_page(user):
    st.title("🆘 Help & Support")

    st.write("Send a message to the program instructor.")

    subject = st.text_input("Subject")
    message = st.text_area("Your Message")

    if st.button("📨 Send Message"):

        if not subject.strip():
            st.error("Please enter a subject.")
            return

        if not message.strip():
            st.error("Please enter a message.")
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

        st.success("✅ Message sent successfully!")
        st.rerun()

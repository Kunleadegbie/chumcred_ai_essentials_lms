
# ui/help.py
import streamlit as st
from datetime import datetime
from services.db import read_conn, write_txn

# --------------------------------------------------
# DB Helpers
# --------------------------------------------------
def create_ticket(user, subject, message):
    with write_txn() as conn:
        conn.execute(
            """
            INSERT INTO support_tickets
            (user_id, username, subject, message, status, created_at)
            VALUES (?, ?, ?, ?, 'open', ?)
            """,
            (
                user["id"],
                user["username"],
                subject,
                message,
                datetime.utcnow().isoformat(),
            ),
        )


def list_student_tickets(user_id):
    with read_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM support_tickets
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
    return rows


def list_all_tickets():
    with read_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM support_tickets
            ORDER BY created_at DESC
            """
        ).fetchall()
    return rows


def reply_ticket(ticket_id, reply, status="replied"):
    with write_txn() as conn:
        conn.execute(
            """
            UPDATE support_tickets
            SET admin_reply = ?, status = ?, replied_at = ?
            WHERE id = ?
            """,
            (reply, status, datetime.utcnow().isoformat(), ticket_id),
        )


# --------------------------------------------------
# UI Router
# --------------------------------------------------
def help_router(user, role="student"):
    st.header("🆘 Help & Support")

    # ===============================
    # STUDENT VIEW
    # ===============================
    if role == "student":
        st.subheader("📨 Submit a Request")

        with st.form("help_form", clear_on_submit=True):
            subject = st.text_input("Subject")
            message = st.text_area("Message", height=150)
            sent = st.form_submit_button("Send")

        if sent:
            if not message.strip():
                st.error("Message cannot be empty.")
            else:
                create_ticket(user, subject, message)
                st.success("✅ Message sent. Admin will respond here.")
                st.rerun()

        st.divider()
        st.subheader("📬 My Requests")

        tickets = list_student_tickets(user["id"])
        if not tickets:
            st.info("No messages yet.")
        else:
            for t in tickets:
                with st.expander(
                    f"{t['subject'] or 'General'} — {t['status'].upper()} — {t['created_at']}"
                ):
                    st.markdown("**Your message:**")
                    st.write(t["message"])

                    if t["admin_reply"]:
                        st.markdown("---")
                        st.markdown("**Admin reply:**")
                        st.write(t["admin_reply"])
                    else:
                        st.info("Awaiting admin response.")

    # ===============================
    # ADMIN VIEW
    # ===============================
    else:
        st.subheader("📥 Student Requests")

        tickets = list_all_tickets()
        if not tickets:
            st.info("No support requests.")
            return

        for t in tickets:
            with st.expander(
                f"{t['username']} — {t['subject'] or 'General'} — {t['status'].upper()}"
            ):
                st.write(f"**Message:** {t['message']}")

                reply = st.text_area(
                    "Reply",
                    value=t["admin_reply"] or "",
                    key=f"reply_{t['id']}",
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Send Reply", key=f"send_{t['id']}"):
                        if reply.strip():
                            reply_ticket(t["id"], reply, "replied")
                            st.success("Reply sent.")
                            st.rerun()
                        else:
                            st.error("Reply cannot be empty.")

                with col2:
                    if st.button("Mark Resolved", key=f"resolve_{t['id']}"):
                        reply_ticket(t["id"], reply or "", "resolved")
                        st.success("Marked resolved.")
                        st.rerun()

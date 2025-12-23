# ui/help.py
from __future__ import annotations

import streamlit as st
from services.db import get_conn


def ensure_support_schema() -> None:
    """
    Self-healing schema: creates support_tickets table if it doesn't exist.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_user_id INTEGER NOT NULL,
            student_username TEXT NOT NULL,

            subject TEXT NOT NULL,
            message TEXT NOT NULL,

            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            status TEXT NOT NULL DEFAULT 'open',      -- open | replied | resolved

            admin_reply TEXT,
            replied_at TEXT,
            replied_by INTEGER
        )
        """
    )

    conn.commit()
    conn.close()


def create_ticket(student_user_id: int, student_username: str, subject: str, message: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO support_tickets (student_user_id, student_username, subject, message)
        VALUES (?, ?, ?, ?)
        """,
        (student_user_id, student_username, subject.strip(), message.strip()),
    )
    conn.commit()
    conn.close()


def list_student_tickets(student_user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, subject, message, created_at, status, admin_reply, replied_at
        FROM support_tickets
        WHERE student_user_id=?
        ORDER BY id DESC
        """,
        (student_user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_all_tickets(status_filter: str = "all", username_filter: str = ""):
    conn = get_conn()
    cur = conn.cursor()

    username_filter = username_filter.strip()

    base = """
        SELECT id, student_user_id, student_username, subject, message, created_at, status, admin_reply, replied_at
        FROM support_tickets
        WHERE 1=1
    """
    params = []

    if status_filter != "all":
        base += " AND status=?"
        params.append(status_filter)

    if username_filter:
        base += " AND student_username LIKE ?"
        params.append(f"%{username_filter}%")

    base += " ORDER BY id DESC"

    cur.execute(base, tuple(params))
    rows = cur.fetchall()
    conn.close()
    return rows


def admin_reply(ticket_id: int, reply: str, admin_user_id: int, resolve: bool = False) -> None:
    conn = get_conn()
    cur = conn.cursor()

    new_status = "resolved" if resolve else "replied"

    cur.execute(
        """
        UPDATE support_tickets
        SET admin_reply=?,
            replied_at=datetime('now'),
            replied_by=?,
            status=?
        WHERE id=?
        """,
        (reply.strip(), admin_user_id, new_status, ticket_id),
    )

    conn.commit()
    conn.close()


def help_router(user: dict, role: str = "student") -> None:
    """
    role: "student" or "admin"
    user must contain: id, username (and role for admin)
    """
    ensure_support_schema()

    if role == "student":
        st.header("🆘 Help & Support")
        st.caption("Send a message to the Admin. You’ll see their reply here.")

        with st.form("support_form", clear_on_submit=True):
            subject = st.text_input("Subject", placeholder="e.g., I can’t upload my Week 2 assignment")
            message = st.text_area("Message", placeholder="Describe the issue clearly...", height=140)
            submitted = st.form_submit_button("Send to Admin", use_container_width=True)

        if submitted:
            if not subject.strip() or not message.strip():
                st.error("Please enter both Subject and Message.")
            else:
                create_ticket(user["id"], user["username"], subject, message)
                st.success("Message sent. Admin will respond here.")
                st.rerun()

        st.divider()
        st.subheader("📩 My Enquiries")

        rows = list_student_tickets(user["id"])
        if not rows:
            st.info("No enquiries yet.")
            return

        for (tid, subject, msg, created_at, status, reply, replied_at) in rows:
            badge = "🟢 OPEN" if status == "open" else ("🟡 REPLIED" if status == "replied" else "✅ RESOLVED")
            with st.expander(f"#{tid} — {subject} — {badge} — {created_at}", expanded=False):
                st.markdown("**Your message:**")
                st.write(msg)

                st.markdown("---")
                if reply:
                    st.markdown("**Admin reply:**")
                    st.write(reply)
                    st.caption(f"Replied at: {replied_at}")
                else:
                    st.info("No reply yet.")

    else:
        # ADMIN VIEW
        st.header("🆘 Help Desk — Admin")
        st.caption("View all student enquiries and respond.")

        c1, c2 = st.columns(2)
        with c1:
            status_filter = st.selectbox("Filter by status", ["all", "open", "replied", "resolved"], index=1)
        with c2:
            username_filter = st.text_input("Search by student username", placeholder="e.g., student1")

        rows = list_all_tickets(status_filter=status_filter, username_filter=username_filter)

        if not rows:
            st.info("No enquiries match your filters.")
            return

        # Select a ticket
        options = [
            f"#{r[0]} | {r[2]} | {r[3]} | {r[6]} | {r[5]}"
            for r in rows
        ]
        chosen = st.selectbox("Select enquiry", options)

        chosen_id = int(chosen.split("|")[0].strip().replace("#", ""))

        # Find selected record
        selected = None
        for r in rows:
            if r[0] == chosen_id:
                selected = r
                break

        if not selected:
            st.error("Could not load selected enquiry.")
            return

        (tid, student_user_id, student_username, subject, msg, created_at, status, existing_reply, replied_at) = selected

        st.markdown(f"### Ticket #{tid}")
        st.write(f"**Student:** {student_username} (ID {student_user_id})")
        st.write(f"**Subject:** {subject}")
        st.write(f"**Status:** {status}")
        st.write(f"**Created:** {created_at}")

        st.markdown("**Student message:**")
        st.write(msg)

        st.markdown("---")
        if existing_reply:
            st.markdown("**Existing admin reply:**")
            st.write(existing_reply)
            st.caption(f"Replied at: {replied_at}")

        st.subheader("✍️ Respond")
        reply = st.text_area("Admin reply", value=existing_reply or "", height=140)

        colA, colB = st.columns(2)
        with colA:
            if st.button("Send Reply (keep open)", use_container_width=True):
                if not reply.strip():
                    st.error("Reply cannot be empty.")
                else:
                    admin_reply(tid, reply, admin_user_id=user["id"], resolve=False)
                    st.success("Reply sent.")
                    st.rerun()

        with colB:
            if st.button("Send Reply + Mark Resolved", use_container_width=True):
                if not reply.strip():
                    st.error("Reply cannot be empty.")
                else:
                    admin_reply(tid, reply, admin_user_id=user["id"], resolve=True)
                    st.success("Reply sent and ticket resolved.")
                    st.rerun()

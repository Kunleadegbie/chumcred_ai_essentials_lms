
# ui/help.py
from __future__ import annotations

import sqlite3
import streamlit as st

from services.db import read_conn, write_txn


def _get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]


def _add_column_if_missing(conn: sqlite3.Connection, table: str, col_def: str) -> None:
    col_name = col_def.split()[0].strip()
    cols = _get_columns(conn, table)
    if col_name not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")


def ensure_support_schema() -> None:
    """
    Creates/migrates support_tickets to match the app's DB schema:
      - user_id, username  (NOT student_user_id)
    This avoids 'no such column: student_user_id' on Railway.
    """
    with write_txn() as conn:
        cur = conn.cursor()

        # Create table in the SAME shape your db.py already uses (user_id/username)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',     -- open | replied | resolved
                admin_reply TEXT,
                created_at TEXT,
                replied_at TEXT,
                replied_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        # Safe migrations (older deployments)
        _add_column_if_missing(conn, "support_tickets", "subject TEXT")
        _add_column_if_missing(conn, "support_tickets", "status TEXT NOT NULL DEFAULT 'open'")
        _add_column_if_missing(conn, "support_tickets", "admin_reply TEXT")
        _add_column_if_missing(conn, "support_tickets", "created_at TEXT")
        _add_column_if_missing(conn, "support_tickets", "replied_at TEXT")
        _add_column_if_missing(conn, "support_tickets", "replied_by INTEGER")

        # Backfill created_at if missing/NULL
        cols = _get_columns(conn, "support_tickets")
        if "created_at" in cols:
            conn.execute(
                """
                UPDATE support_tickets
                SET created_at = COALESCE(created_at, datetime('now'))
                WHERE created_at IS NULL
                """
            )


def create_ticket(user_id: int, username: str, subject: str, message: str) -> None:
    ensure_support_schema()
    subject = (subject or "").strip() or "General enquiry"
    message = (message or "").strip()

    with write_txn() as conn:
        conn.execute(
            """
            INSERT INTO support_tickets (user_id, username, subject, message, created_at, status)
            VALUES (?, ?, ?, ?, datetime('now'), 'open')
            """,
            (int(user_id), username.strip(), subject, message),
        )


def list_student_tickets(user_id: int):
    ensure_support_schema()
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, subject, message, created_at, status, admin_reply, replied_at
            FROM support_tickets
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (int(user_id),),
        )
        return cur.fetchall()


def list_all_tickets(status_filter: str = "all", username_filter: str = ""):
    ensure_support_schema()

    status_filter = (status_filter or "all").strip()
    username_filter = (username_filter or "").strip()

    base = """
        SELECT id, user_id, username, subject, message, created_at, status, admin_reply, replied_at
        FROM support_tickets
        WHERE 1=1
    """
    params: list[object] = []

    if status_filter != "all":
        base += " AND status=?"
        params.append(status_filter)

    if username_filter:
        base += " AND username LIKE ?"
        params.append(f"%{username_filter}%")

    base += " ORDER BY id DESC"

    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(base, tuple(params))
        return cur.fetchall()


def admin_reply(ticket_id: int, reply: str, admin_user_id: int, resolve: bool = False) -> None:
    ensure_support_schema()
    reply = (reply or "").strip()
    new_status = "resolved" if resolve else "replied"

    with write_txn() as conn:
        cols = _get_columns(conn, "support_tickets")
        if "replied_by" in cols:
            conn.execute(
                """
                UPDATE support_tickets
                SET admin_reply=?,
                    replied_at=datetime('now'),
                    replied_by=?,
                    status=?
                WHERE id=?
                """,
                (reply, int(admin_user_id), new_status, int(ticket_id)),
            )
        else:
            conn.execute(
                """
                UPDATE support_tickets
                SET admin_reply=?,
                    replied_at=datetime('now'),
                    status=?
                WHERE id=?
                """,
                (reply, new_status, int(ticket_id)),
            )


def help_router(user: dict, role: str | None = None) -> None:
    """
    role can be forced ("student"/"admin"), otherwise inferred from user["role"].
    user must include: id, username, role
    """
    ensure_support_schema()

    inferred_role = role or user.get("role", "student")
    is_admin = inferred_role == "admin"

    if not is_admin:
        # ---------------- STUDENT VIEW ----------------
        st.header("🆘 Help & Support")
        st.caption("Send an enquiry to the Admin. You will see replies here.")

        with st.form("support_form", clear_on_submit=True):
            subject = st.text_input("Subject", placeholder="e.g., I can’t upload my Week 2 assignment")
            message = st.text_area("Message", placeholder="Describe the issue clearly...", height=140)
            submitted = st.form_submit_button("Send to Admin", use_container_width=True)

        if submitted:
            if not (subject or "").strip() or not (message or "").strip():
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
            title = f"#{tid} — {subject or 'General enquiry'} — {badge} — {created_at}"
            with st.expander(title, expanded=False):
                st.markdown("**Your message:**")
                st.write(msg)

                st.markdown("---")
                if reply:
                    st.markdown("**Admin reply:**")
                    st.write(reply)
                    if replied_at:
                        st.caption(f"Replied at: {replied_at}")
                else:
                    st.info("No reply yet.")

    else:
        # ---------------- ADMIN VIEW ----------------
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

        options = [
            f"#{r[0]} | {r[2]} | {r[3] or 'General'} | {r[6]} | {r[5]}"
            for r in rows
        ]
        chosen = st.selectbox("Select enquiry", options)
        chosen_id = int(chosen.split("|")[0].strip().replace("#", ""))

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
        st.write(f"**Subject:** {subject or 'General enquiry'}")
        st.write(f"**Status:** {status}")
        st.write(f"**Created:** {created_at}")

        st.markdown("**Student message:**")
        st.write(msg)

        st.markdown("---")
        if existing_reply:
            st.markdown("**Existing admin reply:**")
            st.write(existing_reply)
            if replied_at:
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

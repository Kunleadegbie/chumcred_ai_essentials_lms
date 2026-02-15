# --------------------------------------------------
# ui/support.py
# --------------------------------------------------
# Student Help & Support page (SQLite)
#
# Ensures student enquiries are written to the same SQLite DB/table the admin reads.
# Schema-tolerant (handles user_id vs student_user_id; username vs student_username).

from __future__ import annotations

import datetime
from typing import Dict, List, Optional

import streamlit as st

from services.db import DB_PATH, read_conn

# If your codebase has a dedicated write transaction helper, we'll use it.
try:
    from services.db import write_txn  # type: ignore
except Exception:  # pragma: no cover
    write_txn = None  # type: ignore


def _now_sqlite() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


def _cols(conn, table: str) -> List[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _insert_ticket(conn, user: Dict, subject: str, message: str) -> int:
    cols = _cols(conn, "support_tickets")

    # Map columns safely
    uid_col = "user_id" if "user_id" in cols else ("student_user_id" if "student_user_id" in cols else None)
    uname_col = "username" if "username" in cols else ("student_username" if "student_username" in cols else None)

    fields: List[str] = []
    params: List[object] = []

    if uid_col:
        fields.append(uid_col)
        params.append(user.get("id"))

    if uname_col:
        fields.append(uname_col)
        params.append(user.get("username"))

    if "subject" in cols:
        fields.append("subject")
        params.append(subject)

    if "message" in cols:
        fields.append("message")
        params.append(message)

    if "status" in cols:
        fields.append("status")
        params.append("open")

    if "created_at" in cols:
        fields.append("created_at")
        params.append(_now_sqlite())

    if not fields:
        raise RuntimeError("support_tickets has no writable columns. Check schema.")

    placeholders = ", ".join(["?"] * len(fields))
    sql = f"INSERT INTO support_tickets ({', '.join(fields)}) VALUES ({placeholders})"

    cur = conn.execute(sql, params)
    # sqlite integer PK
    ticket_id = cur.lastrowid
    return int(ticket_id) if ticket_id is not None else 0


def support_page(user: Dict):
    st.subheader("🆘 Help & Support")

    # Show DB info (helps verify student/admin hit the same DB)
    st.caption(f"DB_PATH: {DB_PATH}")
    with read_conn() as conn:
        db_row = conn.execute("PRAGMA database_list").fetchone()
        st.caption(f"SQLite file in use: {db_row[2] if db_row else 'unknown'}")

    # Navigation
    if st.button("⬅️ Return to Dashboard", key="support_back_to_dash"):
        st.session_state["page"] = None
        st.rerun()

    # Guard: table must exist
    with read_conn() as conn:
        if not _table_exists(conn, "support_tickets"):
            st.error("Support system is not set up: missing table 'support_tickets'.")
            st.stop()

    st.markdown("Send your question to the admin/instructor. You'll see replies here once addressed.")

    subject = st.text_input("Subject", placeholder="e.g., Week 2 assignment clarification")
    message = st.text_area("Your message", height=160)

    submitted = st.button("Submit Request", type="primary")

    if submitted:
        if not subject.strip() or not message.strip():
            st.error("Please enter both a subject and a message.")
        else:
            try:
                if write_txn is not None:
                    with write_txn() as conn:  # type: ignore
                        ticket_id = _insert_ticket(conn, user, subject.strip(), message.strip())
                        conn.commit()
                else:
                    with read_conn() as conn:
                        ticket_id = _insert_ticket(conn, user, subject.strip(), message.strip())
                        conn.commit()

                st.success(f"✅ Submitted! Ticket ID: {ticket_id if ticket_id else 'created'}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Could not submit your request: {e}")

    st.divider()
    st.markdown("### Your recent tickets")

    # Show student's own tickets if possible
    with read_conn() as conn:
        cols = _cols(conn, "support_tickets")

        uid_col = "user_id" if "user_id" in cols else ("student_user_id" if "student_user_id" in cols else None)
        uname_col = "username" if "username" in cols else ("student_username" if "student_username" in cols else None)

        where_sql = ""
        params: List[object] = []

        if uid_col and user.get("id") is not None:
            where_sql = f"WHERE {uid_col} = ?"
            params = [user.get("id")]
        elif uname_col and user.get("username"):
            where_sql = f"WHERE {uname_col} = ?"
            params = [user.get("username")]

        order_sql = "ORDER BY datetime(created_at) DESC" if "created_at" in cols else "ORDER BY id DESC"

        rows = conn.execute(
            f"SELECT * FROM support_tickets {where_sql} {order_sql} LIMIT 20",
            params,
        ).fetchall()

        tickets = [dict(r) for r in rows] if rows else []

    if not tickets:
        st.info("No tickets yet.")
    else:
        for t in tickets:
            tid = t.get("id")
            status = t.get("status", "open")
            created_at = t.get("created_at", "")
            st.write(f"**#{tid}** — {status} — {created_at}")

            if t.get("subject"):
                st.caption(t.get("subject"))

            if t.get("admin_reply"):
                st.success(f"Admin reply: {t.get('admin_reply')}")

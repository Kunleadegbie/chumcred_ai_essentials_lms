# --------------------------------------------------
# ui/support.py
# --------------------------------------------------
# Student Help & Support page (SQLite)
#
# Key goals:
# - Write NEW student enquiries into the SAME SQLite DB the admin reads.
# - Work across both schemas:
#   A) support_tickets(student_user_id, student_username, ...)
#   B) support_tickets(user_id, username, ...)
# - Make failures obvious (row counts + Ticket ID), without noisy JSON unless debug is enabled.

from __future__ import annotations

import datetime
from typing import Dict, List, Optional, Tuple

import streamlit as st

from services.db import DB_PATH, read_conn


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


def _colnames(conn, table: str) -> List[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _resolve_user_identity(user: Dict) -> Tuple[Optional[object], Optional[str]]:
    """Return (user_id, username) using multiple fallbacks."""
    uid = (
        user.get("id")
        or user.get("user_id")
        or st.session_state.get("id")
        or st.session_state.get("user_id")
    )
    uname = (
        user.get("username")
        or user.get("student_username")
        or user.get("email")
        or st.session_state.get("username")
        or st.session_state.get("email")
    )
    # Ensure username is a string if present
    if uname is not None:
        uname = str(uname)
    return uid, uname


def _insert_support_ticket(conn, user: Dict, subject: str, message: str) -> int:
    cols = _colnames(conn, "support_tickets")

    # map schema differences
    uid_col = "user_id" if "user_id" in cols else ("student_user_id" if "student_user_id" in cols else None)
    uname_col = "username" if "username" in cols else ("student_username" if "student_username" in cols else None)

    user_id, username = _resolve_user_identity(user)

    # If table expects these identifiers, enforce them (prevents silent NOT NULL failures)
    if uid_col and user_id is None:
        raise RuntimeError("Could not determine your user id for ticket submission.")
    if uname_col and not username:
        raise RuntimeError("Could not determine your username for ticket submission.")

    fields: List[str] = []
    params: List[object] = []

    # identifiers
    if uid_col:
        fields.append(uid_col)
        params.append(user_id)
    if uname_col:
        fields.append(uname_col)
        params.append(username)

    # content
    if "subject" in cols:
        fields.append("subject")
        params.append(subject)
    if "message" in cols:
        fields.append("message")
        params.append(message)

    # status / timestamps (only if columns exist)
    if "status" in cols:
        fields.append("status")
        params.append("open")
    if "created_at" in cols:
        fields.append("created_at")
        params.append(_now())

    if not fields:
        raise RuntimeError("support_tickets has no writable columns (unexpected schema).")

    placeholders = ", ".join(["?"] * len(fields))
    sql = f"INSERT INTO support_tickets ({', '.join(fields)}) VALUES ({placeholders})"
    cur = conn.execute(sql, params)

    ticket_id = cur.lastrowid
    try:
        return int(ticket_id) if ticket_id is not None else 0
    except Exception:
        return 0


def support_page(user: Dict):
    st.subheader("🆘 Help & Support")

    # Back button (student)
    if st.button("⬅️ Return to Dashboard", key="support_back_to_dash"):
        st.session_state["page"] = None
        st.rerun()

    # DB proof
    st.caption(f"DB_PATH: {DB_PATH}")
    with read_conn() as conn:
        db_row = conn.execute("PRAGMA database_list").fetchone()
        st.caption(f"SQLite file in use: {db_row[2] if db_row else 'unknown'}")

        if not _table_exists(conn, "support_tickets"):
            st.error("Missing table: support_tickets. Support cannot work until DB is initialized.")
            st.stop()

        cols = _colnames(conn, "support_tickets")
        try:
            cnt = conn.execute("SELECT COUNT(*) FROM support_tickets").fetchone()[0]
        except Exception:
            cnt = "unknown"
        st.caption(f"support_tickets rows (student view): {cnt}")

    st.markdown("Send your question to the admin/instructor. You’ll get a reply here once it’s addressed.")

    subject = st.text_input("Subject", placeholder="e.g., Week 2 assignment clarification")
    message = st.text_area("Your message", height=160, placeholder="Describe your issue clearly...")

    show_debug = st.checkbox("Show debug details", value=False)

    if st.button("Submit Request", type="primary", key="submit_support_ticket"):
        if not subject.strip() or not message.strip():
            st.error("Please enter both a subject and a message.")
            st.stop()

        try:
            with read_conn() as conn:
                before = conn.execute("SELECT COUNT(*) FROM support_tickets").fetchone()[0]
                ticket_id = _insert_support_ticket(conn, user, subject.strip(), message.strip())
                conn.commit()
                after = conn.execute("SELECT COUNT(*) FROM support_tickets").fetchone()[0]

                last_row = None
                try:
                    if ticket_id:
                        last_row = conn.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,)).fetchone()
                    if last_row is None:
                        last_row = conn.execute("SELECT * FROM support_tickets ORDER BY id DESC LIMIT 1").fetchone()
                except Exception:
                    last_row = None

            st.success(f"✅ Submitted! Ticket ID: {ticket_id if ticket_id else 'created'}")
            st.caption(f"Row count: {before} → {after}")

            if show_debug and last_row is not None:
                st.caption("Last saved ticket (debug):")
                st.write(dict(last_row))

            st.rerun()

        except Exception as e:
            st.error(f"❌ Could not submit your request: {e}")

    st.divider()
    st.markdown("### Your recent tickets")

    # Filter to current student if possible
    user_id, username = _resolve_user_identity(user)

    with read_conn() as conn:
        cols = _colnames(conn, "support_tickets")
        uid_col = "user_id" if "user_id" in cols else ("student_user_id" if "student_user_id" in cols else None)
        uname_col = "username" if "username" in cols else ("student_username" if "student_username" in cols else None)

        where_sql = ""
        params: List[object] = []

        if uid_col and user_id is not None:
            where_sql = f"WHERE {uid_col} = ?"
            params = [user_id]
        elif uname_col and username:
            where_sql = f"WHERE {uname_col} = ?"
            params = [username]

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
            title = f"#{tid} • {status} • {created_at}"
            with st.expander(title, expanded=False):
                if t.get("subject"):
                    st.write("**Subject:**", t.get("subject"))
                if t.get("message"):
                    st.write("**Message:**")
                    st.write(t.get("message"))

                if t.get("admin_reply"):
                    st.success(f"Admin reply: {t.get('admin_reply')}")

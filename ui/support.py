# --------------------------------------------------
# ui/support.py
# --------------------------------------------------
# Student Help & Support page (SQLite) — UPDATED (categories + guidance)
#
# Enhancements (minimal changes, same structure):
# - Adds category dropdown (4 categories)
# - Adds response targets guidance
# - Adds structured "feedback before submission" format
# - Stores category in DB if column exists; otherwise prefixes subject with [Category]
#
# Works with BOTH schemas:
# - support_tickets(student_user_id, student_username, ...)
# - support_tickets(user_id, username, ...)

from __future__ import annotations

import datetime
from typing import Dict, List

import streamlit as st

from services.db import read_conn


CATEGORIES = [
    "Can’t access a week",
    "Can’t upload an assignment",
    "Need clarity on a template",
    "Want feedback before submission",
]


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


def _cols(conn, table: str) -> List[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _insert_support_ticket(conn, user: Dict, category: str, subject: str, message: str) -> int:
    cols = _cols(conn, "support_tickets")

    # map schema differences
    uid_col = "user_id" if "user_id" in cols else ("student_user_id" if "student_user_id" in cols else None)
    uname_col = "username" if "username" in cols else ("student_username" if "student_username" in cols else None)

    fields: List[str] = []
    params: List[object] = []

    # user identifiers
    if uid_col:
        fields.append(uid_col)
        params.append(user.get("id"))
    if uname_col:
        fields.append(uname_col)
        params.append(user.get("username"))

    # category storage (preferred)
    if "category" in cols:
        fields.append("category")
        params.append(category)

    # content
    # If no category column, prefix subject with [Category]
    final_subject = subject
    if "category" not in cols and category:
        final_subject = f"[{category}] {subject}"

    if "subject" in cols:
        fields.append("subject")
        params.append(final_subject)
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

    with read_conn() as conn:
        if not _table_exists(conn, "support_tickets"):
            st.error("Missing table: support_tickets. Support cannot work until DB is initialized.")
            st.stop()

    st.markdown(
        "Use this page to ask the instructor/admin for help. "
        "Choose the right category so your request is handled faster."
    )

    # ✅ Response targets (international-style)
    with st.expander("⏱ Response Targets (What to expect)", expanded=False):
        st.write(
            "- **Access/technical issues:** within 24 hours\n"
            "- **Template clarification:** within 48 hours\n"
            "- **Feedback before submission:** within 72 hours (short guidance, not full rewriting)\n"
        )

    # ✅ Category
    category = st.selectbox("Category", CATEGORIES, index=0)

    # Helpful prompt for feedback requests
    if category == "Want feedback before submission":
        st.info(
            "For faster feedback, include:\n"
            "1) Prompt used\n"
            "2) Output received (short)\n"
            "3) What you want improved (tone / structure / accuracy)\n"
        )

    subject = st.text_input("Subject", placeholder="e.g., Week 2 assignment clarification")
    message_placeholder = "Describe your issue clearly..."
    if category == "Want feedback before submission":
        message_placeholder = (
            "Paste in this format:\n\n"
            "PROMPT USED:\n...\n\n"
            "OUTPUT RECEIVED (short):\n...\n\n"
            "WHAT I WANT IMPROVED (pick one): tone / structure / accuracy\n...\n"
        )
    message = st.text_area("Your message", height=200, placeholder=message_placeholder)

    if st.button("Submit Request", type="primary", key="submit_support_ticket"):
        if not subject.strip() or not message.strip():
            st.error("Please enter both a subject and a message.")
            st.stop()

        try:
            with read_conn() as conn:
                ticket_id = _insert_support_ticket(conn, user, category, subject.strip(), message.strip())
                conn.commit()

            st.success(f"✅ Submitted! Ticket ID: {ticket_id if ticket_id else 'created'}")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Could not submit your request: {e}")

    st.divider()
    st.markdown("### Your recent tickets")

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

            # show category if exists, else parse from subject prefix
            cat = t.get("category")
            subj = t.get("subject") or ""
            if not cat and subj.startswith("[") and "]" in subj:
                cat = subj.split("]", 1)[0].replace("[", "").strip()

            title = f"#{tid} • {status} • {created_at}"
            if cat:
                title = f"{title} • {cat}"

            with st.expander(title, expanded=False):
                if t.get("subject"):
                    st.write("**Subject:**", t.get("subject"))
                if t.get("message"):
                    st.write("**Message:**")
                    st.write(t.get("message"))

                if t.get("admin_reply"):
                    st.success(f"Admin reply: {t.get('admin_reply')}")
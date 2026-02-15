# ui/support.py
# Student Help & Support page (SQLite) - schema-tolerant, writes to support_tickets
#
# Fixes the "admin can't see new tickets" problem by:
# - Using the same DB_PATH/read_conn for visibility
# - Detecting correct column names (user_id vs student_user_id, username vs student_username)
# - COMMITTING writes reliably
# - Showing the inserted Ticket ID + timestamp so student knows it saved

from __future__ import annotations

import streamlit as st
import datetime
from services.db import read_conn, DB_PATH

# write_txn exists in your codebase (admin.py uses it). If not, we fallback.
try:
    from services.db import write_txn  # type: ignore
except Exception:
    wri

def _now() -> str:
    # SQLite-friendly timestamp
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

te_txn = None


def _table_exists(conn, table: str) -> bool:
    r = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return r is not None


def _cols(conn, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _insert_ticket(conn, user: dict, subject: str, message: str) -> int:
    cols = _cols(conn, "support_tickets")

    # pick the correct column names based on schema
    uid_col = "user_id" if "user_id" in cols else ("student_user_id" if "student_user_id" in cols else None)
    uname_col = "username" if "username" in cols else ("student_username" if "student_username" in cols else None)

    fields = []
    values = []
    params = []

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

    if \"created_at\" in cols:
        fields.append(\"created_at\")
        params.append(_now())

    if "status" in cols:
        fields.append("status")
        params.append("open")

    # created_at usually has default; only set if column exists and no default in your schema
    # We won't force it unless needed.

    if not fields:
        raise RuntimeError("support_tickets schema has no writable columns (unexpected).")

    sql = f"INSERT INTO support_tickets ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})"
    cur = conn.execute(sql, params)
    # lastrowid works for INTEGER PK; if UUID, this will be None (but your schema shows INTEGER pk in many cases)
    ticket_id = cur.lastrowid
    return int(ticket_id) if ticket_id is not None else 0


def support_page(user: dict):
    st.subheader("🆘 Help & Support")

    # show DB used (helps confirm student writes to same DB admin reads)
    st.caption(f"DB_PATH: {DB_PATH}")
    with read_conn() as conn:
        db_row = conn.execute("PRAGMA database_list").fetchone()
        st.caption(f"SQLite file in use: {db_row[2] if db_row else 'unknown'}")

    # Return button (so you don't lose navigation)
    if st.button("⬅️ Return to Dashboard", key="support_back_to_dash"):
        st.session_state["page"] = None
        st.rerun()

    # ensure table exists
    with read_conn() as conn:
        if not _table_exists(conn, "support_tickets"):
            st.error("Support system is not set up: missing table 'support_tickets'.")
            st.stop()

    st.markdown("Send your question to the admin/instructor. You'll get a reply here when it's addressed.")

    subject = st.text_input("Subject", placeholder="e.g., Week 2 assignment clarification")
    message = st.text_area("Your message", height=160)

    col1, col2 = st.columns([1, 2])
    with col1:
        submit = st.button("Submit Request", type="primary")
    with col2:
        st.caption("Tip: Be specific (week, task, what you've tried, error message).")

    if submit:
        if not subject.strip() or not message.strip():
            st.error("Please enter both a subject and a message.")
        else:
            try:
                if write_txn is not None:
                    with write_txn() as conn:
                        ticket_id = _insert_ticket(conn, user, subject.strip(), message.strip())
                        conn.commit()
                else:
                    # fallback if write_txn isn't available
                    with read_conn() as conn:
                        ticket_id = _insert_ticket(conn, user, subject.strip(), message.strip())
                        conn.commit()

                st.success(f"✅ Submitted! Ticket ID: {ticket_id or 'created'}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Could not submit your request: {e}")

    st.divider()
    st.markdown("### Your recent tickets")

    # show student's own tickets if possible
    with read_conn() as conn:
        cols = _cols(conn, "support_tickets")
        uid_col = "user_id" if "user_id" in cols else ("student_user_id" if "student_user_id" in cols else None)
        where = ""
        params = []

        if uid_col:
            where = f"WHERE {uid_col} = ?"
            params = [user.get("id")]

        order_sql = "ORDER BY datetime(created_at) DESC" if "created_at" in cols else "ORDER BY id DESC"

        cur = conn.execute(f"SELECT * FROM support_tickets {where} {order_sql} LIMIT 20", params)
        rows = cur.fetchall()
        items = [dict(zip([d[0] for d in cur.description], r)) for r in rows]

    if not items:
        st.info("No tickets yet.")
    else:
        for t in items:
            tid = t.get("id")
            st.write(f"**#{tid}** — {t.get('status','open')} — {t.get('created_at','')}")
            if "admin_reply" in t and t.get("admin_reply"):
                st.success(f"Admin reply: {t.get('admin_reply')}")
            st.caption(t.get("subject",""))

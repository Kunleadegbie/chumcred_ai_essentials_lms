# ui/admin_support.py
# Admin Help & Support page (SQLite) - designed to match student support writes.

from __future__ import annotations

import streamlit as st
import pandas as pd

from services.db import read_conn, DB_PATH


def _rows_to_dicts(cur, rows):
    cols = [d[0] for d in cur.description] if cur and cur.description else []
    return [dict(zip(cols, r)) for r in rows]


def _table_exists(conn, table: str) -> bool:
    try:
        r = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (table,),
        ).fetchone()
        return r is not None
    except Exception:
        return False


def _table_cols(conn, table: str) -> list[str]:
    try:
        return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


def admin_support_page(user: dict | None = None):
    st.subheader("🆘 Help & Support (Student Enquiries)")

    # Show DB config (very important for debugging path mismatches)
    st.caption(f"DB_PATH: {DB_PATH}")

    with read_conn() as conn:
        db_row = conn.execute("PRAGMA database_list").fetchone()
        st.caption(f"SQLite file in use: {db_row[2] if db_row else 'unknown'}")

        if not _table_exists(conn, "support_tickets"):
            st.error("Table 'support_tickets' not found in this DB.")
            return

        # Counts
        tickets_count = conn.execute("SELECT COUNT(*) FROM support_tickets").fetchone()[0]
        msgs_count = conn.execute("SELECT COUNT(*) FROM support_messages").fetchone()[0] if _table_exists(conn, "support_messages") else 0

        st.write(f"support_tickets rows: **{tickets_count}**")
        st.write(f"support_messages rows: **{msgs_count}**")

        # Filters
        status = st.selectbox("Filter by status", ["All", "open", "in_progress", "resolved", "closed"], index=0)
        q = st.text_input("Search (subject/message/username)", value="").strip()

        cols = _table_cols(conn, "support_tickets")

        # Build a robust query that doesn't assume specific columns exist
        where = []
        params = []

        if status != "All" and "status" in cols:
            where.append("status = ?")
            params.append(status)

        # search
        if q:
            like = f"%{q}%"
            search_parts = []
            for c in ["subject", "message", "student_username"]:
                if c in cols:
                    search_parts.append(f"{c} LIKE ?")
                    params.append(like)
            if search_parts:
                where.append("(" + " OR ".join(search_parts) + ")")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        order_sql = "ORDER BY datetime(created_at) DESC" if "created_at" in cols else "ORDER BY id DESC"

        cur = conn.execute(
            f"SELECT * FROM support_tickets {where_sql} {order_sql} LIMIT 200",
            params,
        )
        rows = cur.fetchall()
        tickets = _rows_to_dicts(cur, rows)

    if not tickets:
        st.info("No tickets match the current filter.")
        st.stop()

    # Show as table + expandable details
    st.dataframe(pd.DataFrame(tickets), use_container_width=True)

    st.divider()
    st.subheader("Ticket details")

    # Choose ticket
    id_key = "id" if "id" in tickets[0] else list(tickets[0].keys())[0]
    ids = [t.get(id_key) for t in tickets]
    selected = st.selectbox("Select ticket", ids)

    t = next((x for x in tickets if x.get(id_key) == selected), None)
    if not t:
        st.stop()

    st.json(t)

    # Admin actions (only if columns exist)
    st.subheader("Admin actions")
    status_col_exists = "status" in t
    reply_col_exists = "admin_reply" in t

    new_status = None
    if status_col_exists:
        new_status = st.selectbox(
            "Update status",
            ["open", "in_progress", "resolved", "closed"],
            index=["open", "in_progress", "resolved", "closed"].index(t.get("status", "open")) if t.get("status") in ["open", "in_progress", "resolved", "closed"] else 0,
        )

    reply_text = ""
    if reply_col_exists:
        reply_text = st.text_area("Admin reply", value=t.get("admin_reply") or "", height=120)

    if st.button("Save update", type="primary"):
        with read_conn() as conn:
            cols = _table_cols(conn, "support_tickets")
            sets = []
            params = []

            if status_col_exists and "status" in cols:
                sets.append("status = ?")
                params.append(new_status)

            if reply_col_exists and "admin_reply" in cols:
                sets.append("admin_reply = ?")
                params.append(reply_text.strip())

            # optional audit fields if they exist
            if "replied_at" in cols:
                sets.append("replied_at = datetime('now')")
            if "replied_by" in cols and user and "id" in user:
                sets.append("replied_by = ?")
                params.append(user["id"])

            if not sets:
                st.warning("No updatable columns found in support_tickets (status/admin_reply/replied_at/replied_by).")
            else:
                params.append(selected)
                conn.execute(
                    f"UPDATE support_tickets SET {', '.join(sets)} WHERE {id_key} = ?",
                    params,
                )
                conn.commit()

        st.success("Saved.")
        st.rerun()

    # Optional: show latest messages if available
    if "support_messages" in ["support_messages"]:
        st.divider()
        st.subheader("Latest support messages (raw)")
        try:
            with read_conn() as conn:
                if _table_exists(conn, "support_messages"):
                    cur = conn.execute("SELECT * FROM support_messages ORDER BY id DESC LIMIT 200")
                    rows = cur.fetchall()
                    msgs = _rows_to_dicts(cur, rows)
                    if msgs:
                        st.dataframe(pd.DataFrame(msgs), use_container_width=True)
                    else:
                        st.info("No rows in support_messages.")
        except Exception as e:
            st.warning(f"Could not load support_messages: {e}")

# --------------------------------------------------
# ui/admin_support.py
# --------------------------------------------------
# Admin Help & Support (SQLite) — actionable inbox
#
# Reads from support_tickets and lets admin:
# - filter/search
# - open each ticket
# - reply + change status

from __future__ import annotations

import streamlit as st
import pandas as pd

from services.db import read_conn, DB_PATH


def _table_exists(conn, table: str) -> bool:
    r = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return r is not None


def _cols(conn, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _fetch(status: str, q: str) -> tuple[list[dict], list[str]]:
    with read_conn() as conn:
        if not _table_exists(conn, "support_tickets"):
            return [], []

        cols = _cols(conn, "support_tickets")
        where = []
        params: list[object] = []

        if status != "All" and "status" in cols:
            where.append("status = ?")
            params.append(status)

        if q:
            like = f"%{q}%"
            search_cols = [c for c in ["subject", "message", "username", "student_username"] if c in cols]
            if search_cols:
                where.append("(" + " OR ".join([f"{c} LIKE ?" for c in search_cols]) + ")")
                params.extend([like] * len(search_cols))

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        order_sql = "ORDER BY datetime(created_at) DESC" if "created_at" in cols else "ORDER BY id DESC"

        cur = conn.execute(f"SELECT * FROM support_tickets {where_sql} {order_sql} LIMIT 500", params)
        rows = cur.fetchall()
        tickets = [dict(r) for r in rows] if rows else []
        return tickets, cols


def _update(ticket_id: int, id_key: str, new_status: str | None, reply: str | None, admin_user: dict | None) -> tuple[bool, str]:
    with read_conn() as conn:
        if not _table_exists(conn, "support_tickets"):
            return False, "support_tickets not found."

        cols = _cols(conn, "support_tickets")
        sets = []
        params: list[object] = []

        if new_status is not None and "status" in cols:
            sets.append("status = ?")
            params.append(new_status)

        if reply is not None and "admin_reply" in cols:
            sets.append("admin_reply = ?")
            params.append(reply)

        if "replied_at" in cols:
            sets.append("replied_at = datetime('now')")

        if "replied_by" in cols and admin_user and "id" in admin_user:
            sets.append("replied_by = ?")
            params.append(admin_user["id"])

        if not sets:
            return False, "No updatable columns (need status/admin_reply)."

        params.append(ticket_id)
        conn.execute(f"UPDATE support_tickets SET {', '.join(sets)} WHERE {id_key} = ?", params)
        conn.commit()
        return True, "Saved."


def admin_support_page(user: dict | None = None):
    st.subheader("🆘 Help & Support (Student Enquiries)")

    # DB proof + quick stats
    st.caption(f"DB_PATH: {DB_PATH}")
    with read_conn() as conn:
        db_row = conn.execute("PRAGMA database_list").fetchone()
        st.caption(f"SQLite file in use: {db_row[2] if db_row else 'unknown'}")

        if _table_exists(conn, "support_tickets"):
            cnt = conn.execute("SELECT COUNT(*) FROM support_tickets").fetchone()[0]
            st.caption(f"support_tickets rows: {cnt}")
            try:
                last = conn.execute("SELECT id, created_at FROM support_tickets ORDER BY id DESC LIMIT 1").fetchone()
                if last:
                    st.caption(f"Latest ticket: id={last[0]} created_at={last[1]}")
            except Exception:
                pass
        else:
            st.error("support_tickets table not found.")
            st.stop()

    c1, c2, c3, c4 = st.columns([1.1, 1.9, 1.2, 0.9])
    with c1:
        status = st.selectbox("Status", ["All", "open", "in_progress", "resolved", "closed"], index=0)
    with c2:
        q = st.text_input("Search (subject/message/username)", value="").strip()
    with c3:
        view_mode = st.selectbox("View", ["Action view", "Table view"], index=0)
    with c4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    show_debug = st.checkbox("Show debug", value=False)

    tickets, cols = _fetch(status=status, q=q)

    if show_debug:
        st.write("Detected support_tickets columns:")
        st.write(cols)

    if not tickets:
        st.info(f"No enquiries found (filters: status={status}, search='{q}').")
        return

    if view_mode == "Table view":
        st.dataframe(pd.DataFrame(tickets), use_container_width=True)
        st.caption("Switch to Action view to reply and update status.")
        return

    id_key = "id" if "id" in cols else "id"

    for t in tickets:
        tid = t.get(id_key)
        who = t.get("username") or t.get("student_username") or t.get("user_id") or t.get("student_user_id") or "student"
        when = t.get("created_at") or ""
        cur_status = t.get("status") or "open"

        title = f"#{tid} • {who} • {cur_status} • {when}"
        with st.expander(title, expanded=False):
            if t.get("subject") is not None:
                st.write("**Subject:**", t.get("subject"))
            if t.get("message") is not None:
                st.write("**Message:**")
                st.write(t.get("message"))

            st.divider()

            can_status = "status" in cols
            can_reply = "admin_reply" in cols

            left, right = st.columns([1, 2])

            new_status = None
            if can_status:
                options = ["open", "in_progress", "resolved", "closed"]
                try:
                    idx = options.index(cur_status)
                except Exception:
                    idx = 0
                new_status = left.selectbox("Update status", options, index=idx, key=f"st_{tid}")

            reply_text = None
            if can_reply:
                reply_text = right.text_area("Reply", value=(t.get("admin_reply") or ""), height=120, key=f"rp_{tid}")

            b1, b2 = st.columns([1, 1])
            if b1.button("Save", type="primary", key=f"save_{tid}"):
                ok, msg = _update(int(tid), id_key, (new_status if can_status else None), (reply_text or ""), user)
                st.success(msg) if ok else st.warning(msg)
                st.rerun()

            if can_status and b2.button("Mark Resolved", key=f"res_{tid}"):
                ok, msg = _update(int(tid), id_key, "resolved", (reply_text or ""), user)
                st.success("Marked resolved.") if ok else st.warning(msg)
                st.rerun()

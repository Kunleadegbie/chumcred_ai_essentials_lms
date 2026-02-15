# ui/admin_support.py
# Admin Help & Support page (SQLite) - schema-tolerant and actionable
# - Reads from support_tickets (and optionally support_messages)
# - Action view for replying + status updates
# - No raw JSON unless Debug is enabled

from __future__ import annotations

import streamlit as st
import pandas as pd

from services.db import read_conn, DB_PATH


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


def _rows_to_dicts(cur, rows) -> list[dict]:
    colnames = [d[0] for d in cur.description] if cur and cur.description else []
    return [dict(zip(colnames, r)) for r in rows]


def _fetch_tickets(status: str, q: str) -> tuple[list[dict], list[str]]:
    with read_conn() as conn:
        if not _table_exists(conn, "support_tickets"):
            return [], []

        cols = _table_cols(conn, "support_tickets")

        where = []
        params = []

        # status filter
        if status != "All" and "status" in cols:
            where.append("status = ?")
            params.append(status)

        # search filter
        if q:
            like = f"%{q}%"
            search_cols = [c for c in ["subject", "message", "username", "student_username"] if c in cols]
            if search_cols:
                where.append("(" + " OR ".join([f"{c} LIKE ?" for c in search_cols]) + ")")
                params.extend([like] * len(search_cols))

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        order_sql = "ORDER BY datetime(created_at) DESC" if "created_at" in cols else "ORDER BY id DESC"

        cur = conn.execute(
            f"SELECT * FROM support_tickets {where_sql} {order_sql} LIMIT 500",
            params,
        )
        rows = cur.fetchall()
        return _rows_to_dicts(cur, rows), cols


def _update_ticket(ticket_id, id_key: str, new_status: str | None, admin_reply: str | None, admin_user: dict | None):
    with read_conn() as conn:
        if not _table_exists(conn, "support_tickets"):
            return False, "Table 'support_tickets' not found."

        cols = _table_cols(conn, "support_tickets")
        sets = []
        params = []

        if new_status is not None and "status" in cols:
            sets.append("status = ?")
            params.append(new_status)

        if admin_reply is not None and "admin_reply" in cols:
            sets.append("admin_reply = ?")
            params.append(admin_reply)

        if "replied_at" in cols:
            sets.append("replied_at = datetime('now')")

        # replied_by may be integer or text; store whatever user['id'] is
        if "replied_by" in cols and admin_user and isinstance(admin_user, dict) and "id" in admin_user:
            sets.append("replied_by = ?")
            params.append(admin_user["id"])

        if not sets:
            return False, "No updatable columns found (expected status/admin_reply)."

        params.append(ticket_id)
        conn.execute(
            f"UPDATE support_tickets SET {', '.join(sets)} WHERE {id_key} = ?",
            params,
        )
        conn.commit()
        return True, "Saved."


def admin_support_page(user: dict | None = None):
    st.subheader("🆘 Help & Support (Student Enquiries)")

    # Confirm DB file (helps detect path mismatches)
    st.caption(f"DB_PATH: {DB_PATH}")
    try:
        with read_conn() as conn:
            db_row = conn.execute("PRAGMA database_list").fetchone()
            st.caption(f"SQLite file in use: {db_row[2] if db_row else 'unknown'}")
            # show row count for quick sanity
            if _table_exists(conn, "support_tickets"):
                cnt = conn.execute("SELECT COUNT(*) FROM support_tickets").fetchone()[0]
                st.caption(f"support_tickets rows: {cnt}")
    except Exception:
        pass

    # Filters / mode
    c1, c2, c3, c4 = st.columns([1.1, 1.7, 1.2, 0.9])
    with c1:
        status = st.selectbox("Status", ["All", "open", "in_progress", "resolved", "closed"], index=0)
    with c2:
        q = st.text_input("Search (subject/message/username)", value="").strip()
    with c3:
        view_mode = st.selectbox("View", ["Action view", "Table view"], index=0)
    with c4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    show_debug = st.checkbox("Show debug panels", value=False)

    tickets, cols = _fetch_tickets(status=status, q=q)

    if not tickets:
        st.info("No enquiries found (or none match your filters).")
        if show_debug:
            st.write("Detected support_tickets columns:", cols)
        st.stop()

    id_key = "id" if "id" in cols else (list(tickets[0].keys())[0] if tickets else "id")

    if view_mode == "Table view":
        st.dataframe(pd.DataFrame(tickets), use_container_width=True)
        st.caption("Switch to **Action view** to reply, change status, and close tickets.")
        if show_debug:
            st.write("Detected support_tickets columns:", cols)
        st.stop()

    st.caption("Expand a ticket to reply and update status. Use filters to focus on open enquiries.")

    for t in tickets:
        ticket_id = t.get(id_key)
        who = (
            t.get("username")
            or t.get("student_username")
            or t.get("student_user_id")
            or t.get("user_id")
            or "student"
        )
        when = t.get("created_at") or ""
        current_status = t.get("status") or "open"

        title = f"#{ticket_id} • {who} • {current_status} • {when}"
        with st.expander(title, expanded=False):
            # Clean display
            if "subject" in t:
                st.write("**Subject:**", t.get("subject"))
            if "message" in t:
                st.write("**Message:**")
                st.write(t.get("message"))

            st.divider()

            can_status = "status" in cols
            can_reply = "admin_reply" in cols

            colA, colB = st.columns([1, 2])

            new_status = None
            if can_status:
                try:
                    idx = ["open", "in_progress", "resolved", "closed"].index(current_status)
                except Exception:
                    idx = 0

                new_status = colA.selectbox(
                    "Update status",
                    ["open", "in_progress", "resolved", "closed"],
                    index=idx,
                    key=f"status_{ticket_id}",
                )

            reply_text = None
            if can_reply:
                reply_text = colB.text_area(
                    "Reply to student",
                    value=(t.get("admin_reply") or ""),
                    height=120,
                    key=f"reply_{ticket_id}",
                )

            b1, b2, b3 = st.columns([1, 1, 2])

            if b1.button("Save", type="primary", key=f"save_{ticket_id}"):
                ok, msg = _update_ticket(
                    ticket_id=ticket_id,
                    id_key=id_key,
                    new_status=(new_status if can_status else None),
                    admin_reply=(reply_text.strip() if reply_text is not None else None),
                    admin_user=user,
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.warning(msg)

            if can_status and b2.button("Mark Resolved", key=f"resolve_{ticket_id}"):
                ok, msg = _update_ticket(
                    ticket_id=ticket_id,
                    id_key=id_key,
                    new_status="resolved",
                    admin_reply=(reply_text.strip() if reply_text is not None else None),
                    admin_user=user,
                )
                if ok:
                    st.success("Marked as resolved.")
                    st.rerun()
                else:
                    st.warning(msg)

            if show_debug:
                with b3.expander("Debug"):
                    st.write("Detected columns:", cols)
                    st.write("Ticket keys present:", list(t.keys()))
                    st.write("id_key:", id_key)



# ui/admin.py 
# new additions
from __future__ import annotations

import os
from typing import List, Dict

import streamlit as st
from services.db import get_conn
from ui.help import help_router

TOTAL_WEEKS = 6


def _fetchall(sql: str, params: tuple = ()) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def _execute(sql: str, params: tuple = ()) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    rc = cur.rowcount
    conn.close()
    return rc


def _ensure_core_tables():
    """
    Kept as-is (from your uploaded script) to avoid breaking existing local DBs.
    If you're already using services/db.py init_db(), this will simply no-op for existing tables.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            password TEXT,
            role TEXT NOT NULL DEFAULT 'student',
            cohort TEXT DEFAULT 'Cohort 1'
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'locked',
            UNIQUE(user_id, week)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            original_filename TEXT,
            submitted_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'submitted',   -- submitted|approved|rejected
            grade REAL,
            feedback TEXT,
            reviewed_at TEXT,
            reviewed_by INTEGER,
            UNIQUE(user_id, week)
        )
        """
    )

    conn.commit()
    conn.close()


def _get_students() -> List[Dict]:
    rows = _fetchall(
        """
        SELECT id, username, COALESCE(cohort,'Cohort 1')
        FROM users
        WHERE role='student'
        ORDER BY username
        """
    )
    return [{"id": r[0], "username": r[1], "cohort": r[2]} for r in rows]


def _get_cohorts() -> List[str]:
    rows = _fetchall(
        """
        SELECT DISTINCT COALESCE(cohort,'Cohort 1')
        FROM users
        WHERE role='student'
        ORDER BY 1
        """
    )
    cohorts = [r[0] for r in rows]
    return cohorts if cohorts else ["Cohort 1"]


def _seed_progress_for_user(user_id: int):
    # Week 1 unlocked; Weeks 2–6 locked (admin controls access)
    for w in range(1, TOTAL_WEEKS + 1):
        status = "unlocked" if w == 1 else "locked"
        _execute(
            """
            INSERT OR IGNORE INTO progress (user_id, week, status)
            VALUES (?, ?, ?)
            """,
            (user_id, w, status),
        )


def _set_week_status(user_id: int, week: int, status: str):
    _execute(
        """
        INSERT OR IGNORE INTO progress (user_id, week, status)
        VALUES (?, ?, ?)
        """,
        (user_id, week, status),
    )
    _execute(
        """
        UPDATE progress
        SET status=?
        WHERE user_id=? AND week=?
        """,
        (status, user_id, week),
    )


def _set_week_status_by_cohort(cohort: str, week: int, status: str) -> int:
    rows = _fetchall(
        """
        SELECT id
        FROM users
        WHERE role='student' AND COALESCE(cohort,'Cohort 1')=?
        """,
        (cohort,),
    )
    n = 0
    for (uid,) in rows:
        _set_week_status(uid, week, status)
        n += 1
    return n


def _mark_week_completed(user_id: int, week: int):
    # does NOT auto-unlock next week
    _set_week_status(user_id, week, "completed")


def _page_dashboard(admin_user: dict):
    st.header("🛠 Admin Dashboard")
    st.write(f"Welcome, **{admin_user['username']}**")
    students = _get_students()
    cohorts = _get_cohorts()
    st.metric("Total Students", len(students))
    st.metric("Cohorts", len(cohorts))
    st.info(
        "Policy: Students do NOT access Week 2–6 until Admin unlocks them. "
        "Completion does NOT auto-unlock next week."
    )


def _page_all_students():
    """
    NEW: All Students table/page (your requested feature).
    Uses services.auth.get_all_students() for richer columns and reliable reading on Railway.
    """
    st.header("👥 All Students")
    st.caption("View all created students. Use filters to find cohorts quickly.")

    try:
        from services.auth import get_all_students, get_all_cohorts  # type: ignore
    except Exception as e:
        st.error(f"All Students page unavailable (auth import error): {e}")
        return

    cohorts = ["All"] + (get_all_cohorts() or ["Cohort 1"])
    selected_cohort = st.selectbox("Filter by cohort", cohorts, index=0)

    rows = get_all_students()  # list[dict]
    if selected_cohort != "All":
        rows = [r for r in rows if (r.get("cohort") or "Cohort 1") == selected_cohort]

    if not rows:
        st.info("No students found for this filter.")
        return

    # Make a clean dataframe-like list with predictable column order
    table = []
    for r in rows:
        table.append(
            {
                "ID": r.get("id"),
                "Username": r.get("username"),
                "Full Name": r.get("full_name") or "",
                "Email": r.get("email") or "",
                "Cohort": r.get("cohort") or "Cohort 1",
                "Active": "Yes" if int(r.get("active") or 0) == 1 else "No",
                "Created At": r.get("created_at") or "",
            }
        )

    st.dataframe(table, use_container_width=True)

    # Optional CSV export
    try:
        import csv
        import io

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)
        st.download_button(
            "⬇️ Download CSV",
            data=buf.getvalue().encode("utf-8"),
            file_name="all_students.csv",
            mime="text/csv",
            use_container_width=True,
        )
    except Exception:
        pass


def _page_create_student():
    st.header("➕ Create Student")

    username = st.text_input("Student Username")
    password = st.text_input("Password", type="password")
    cohort = st.text_input("Cohort", value="Cohort 1")

    if st.button("Create Student", use_container_width=True):
        if not username or not password:
            st.error("Username and password are required.")
            return

        user_id = None
        try:
            from services.auth import create_user  # type: ignore
            user_id = create_user(
                username=username.strip(),
                password=password,
                role="student",
                cohort=cohort.strip(),
            )
        except Exception:
            import hashlib

            pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
            cols = _fetchall("PRAGMA table_info(users)")
            colnames = [c[1] for c in cols]

            try:
                if "password_hash" in colnames:
                    _execute(
                        "INSERT INTO users (username, password_hash, role, cohort) VALUES (?, ?, 'student', ?)",
                        (username.strip(), pw_hash, cohort.strip() or "Cohort 1"),
                    )
                else:
                    _execute(
                        "INSERT INTO users (username, password, role, cohort) VALUES (?, ?, 'student', ?)",
                        (username.strip(), pw_hash, cohort.strip() or "Cohort 1"),
                    )
                uid_row = _fetchall("SELECT id FROM users WHERE username=?", (username.strip(),))
                user_id = uid_row[0][0] if uid_row else None
            except Exception as e:
                st.error(f"Could not create student: {e}")
                return

        if not user_id:
            st.error("Student not created (possibly username already exists).")
            return

        _seed_progress_for_user(int(user_id))
        st.success(f"Student created: {username} (ID: {user_id})")


def _page_cohort_lock_unlock():
    st.header("🧩 Cohort Bulk Lock/Unlock")
    cohort = st.selectbox("Select Cohort", _get_cohorts())
    week = st.selectbox("Week", list(range(1, TOTAL_WEEKS + 1)), index=1)
    status = st.selectbox("Set status", ["locked", "unlocked"])

    if st.button("Apply to Cohort", use_container_width=True):
        n = _set_week_status_by_cohort(cohort, int(week), status)
        st.success(f"Updated {n} students in {cohort}: Week {week} -> {status}")


def _page_individual_week_control():
    st.header("🎯 Individual Week Control")
    students = _get_students()
    if not students:
        st.info("No students yet. Create a student first.")
        return

    labels = [f"{s['username']} (ID {s['id']}) — {s['cohort']}" for s in students]
    idx = st.selectbox("Select Student", list(range(len(labels))), format_func=lambda i: labels[i])
    s = students[idx]

    week = st.selectbox("Week", list(range(1, TOTAL_WEEKS + 1)), index=1)
    status = st.selectbox("Set status", ["locked", "unlocked", "completed"])

    if st.button("Update Week Status", use_container_width=True):
        _set_week_status(s["id"], int(week), status)
        st.success(f"{s['username']}: Week {week} -> {status}")


def _page_assignment_review(admin_user: dict):
    st.header("📤 Assignment Review & Grading")
    st.caption("Approve/Reject submissions. Approval marks week as completed. No auto-unlock.")

    status_filter = st.selectbox("Filter", ["all", "submitted", "approved", "rejected"], index=1)

    if status_filter == "all":
        rows = _fetchall(
            """
            SELECT a.id, u.username, a.user_id, a.week, a.file_path, a.original_filename,
                   a.status, a.grade, a.submitted_at
            FROM assignments a
            JOIN users u ON u.id = a.user_id
            ORDER BY a.submitted_at DESC
            """
        )
    else:
        rows = _fetchall(
            """
            SELECT a.id, u.username, a.user_id, a.week, a.file_path, a.original_filename,
                   a.status, a.grade, a.submitted_at
            FROM assignments a
            JOIN users u ON u.id = a.user_id
            WHERE a.status=?
            ORDER BY a.submitted_at DESC
            """,
            (status_filter,),
        )

    if not rows:
        st.info("No assignments found for this filter.")
        return

    for (aid, username, user_id, week, file_path, original_filename, status, grade, submitted_at) in rows:
        with st.expander(f"{username} | Week {week} | {status.upper()} | {submitted_at}", expanded=False):
            st.write(f"**Student:** {username} (ID {user_id})")
            st.write(f"**Week:** {week}")
            st.write(f"**Status:** {status}")
            st.write(f"**Submitted:** {submitted_at}")

            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download submission (PDF)",
                        data=f,
                        file_name=original_filename or f"{username}_week{week}.pdf",
                        mime="application/pdf",
                        key=f"dl_{aid}",
                        use_container_width=True,
                    )
            else:
                st.error("File not found on disk. Check your assignments upload path.")

            st.markdown("### ✅ Grade & Decision")
            new_grade = st.number_input(
                "Grade (0–100)",
                min_value=0.0,
                max_value=100.0,
                value=float(grade) if grade is not None else 0.0,
                step=1.0,
                key=f"g_{aid}",
            )
            feedback = st.text_area("Feedback (optional)", key=f"fb_{aid}")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Approve", key=f"ap_{aid}", use_container_width=True):
                    _execute(
                        """
                        UPDATE assignments
                        SET status='approved', grade=?, feedback=?, reviewed_at=datetime('now'), reviewed_by=?
                        WHERE id=?
                        """,
                        (new_grade, feedback, admin_user["id"], aid),
                    )
                    _mark_week_completed(int(user_id), int(week))
                    st.success("Approved and saved.")
                    st.rerun()

            with c2:
                if st.button("Reject", key=f"rj_{aid}", use_container_width=True):
                    _execute(
                        """
                        UPDATE assignments
                        SET status='rejected', grade=?, feedback=?, reviewed_at=datetime('now'), reviewed_by=?
                        WHERE id=?
                        """,
                        (new_grade, feedback, admin_user["id"], aid),
                    )
                    st.warning("Rejected. Student can resubmit.")
                    st.rerun()


def _page_gradebook():
    st.header("📊 Gradebook")
    rows = _fetchall(
        """
        SELECT u.username, COALESCE(u.cohort,'Cohort 1'), a.week, a.status, a.grade, a.submitted_at, a.reviewed_at
        FROM assignments a
        JOIN users u ON u.id = a.user_id
        ORDER BY u.username, a.week
        """
    )
    if not rows:
        st.info("No submissions/grades yet.")
        return

    data = []
    for username, cohort, week, status, grade, submitted_at, reviewed_at in rows:
        data.append(
            {
                "Student": username,
                "Cohort": cohort,
                "Week": week,
                "Assignment Status": status,
                "Grade": "" if grade is None else grade,
                "Submitted": submitted_at,
                "Reviewed": reviewed_at or "",
            }
        )
    st.dataframe(data, use_container_width=True)


def admin_router(user: dict):
    _ensure_core_tables()

    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=150)
        elif os.path.exists(os.path.join("assets", "logo.png")):
            st.image(os.path.join("assets", "logo.png"), width=150)

        st.markdown("### 🛠 Admin Menu")
        st.markdown(f"**User:** {user['username']}")

        menu = st.radio(
            "Navigate",
            [
                "Dashboard",
                "All Students",          # NEW
                "Create Student",
                "Cohort Lock/Unlock",
                "Individual Week Control",
                "Assignment Review",
                "Gradebook",
                "Help Inbox",
            ],
            index=0,
        )

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    if menu == "Dashboard":
        _page_dashboard(user)
    elif menu == "All Students":
        _page_all_students()
    elif menu == "Create Student":
        _page_create_student()
    elif menu == "Cohort Lock/Unlock":
        _page_cohort_lock_unlock()
    elif menu == "Individual Week Control":
        _page_individual_week_control()
    elif menu == "Assignment Review":
        _page_assignment_review(user)
    elif menu == "Gradebook":
        _page_gradebook()
    elif menu == "Help Inbox":
        help_router(user, role="admin")

import os
import re
from datetime import datetime
import streamlit as st

from services.progress import (
    get_progress,
    mark_week_completed,
)

from services.assignments import (
    can_issue_certificate,
)

from services.certificates import has_certificate, issue_certificate
from services.db import read_conn


CONTENT_DIR = "content"
TOTAL_WEEKS = 6

# Where uploaded assignment files are stored (server)
ASSIGNMENTS_UPLOAD_ROOT = "/app/data/uploads/assignments"


def _safe_filename(name: str) -> str:
    """Keep filenames simple and filesystem-safe."""
    name = name.strip()
    name = re.sub(r"[^\w\-. ]+", "", name)
    name = name.replace(" ", "_")
    return name or "assignment_file"


def _table_columns(conn, table_name: str) -> set[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        # PRAGMA table_info returns rows with columns: cid, name, type, notnull, dflt_value, pk
        return {r[1] if isinstance(r, (tuple, list)) else r["name"] for r in rows}
    except Exception:
        return set()


def _insert_assignment_row(conn, cols: set[str], payload: dict) -> None:
    """
    Insert into assignments table using only columns that exist.
    This prevents crashes if your schema differs.
    """
    usable = {k: v for k, v in payload.items() if k in cols}
    if not usable:
        # Nothing matched schema; fail loudly so you notice
        raise RuntimeError("Assignments table schema did not match expected fields.")

    keys = list(usable.keys())
    placeholders = ", ".join(["?"] * len(keys))
    sql = f"INSERT INTO assignments ({', '.join(keys)}) VALUES ({placeholders})"
    conn.execute(sql, tuple(usable[k] for k in keys))
    conn.commit()


def _fetch_assignments(conn, user_id: str, week: int):
    """
    Pull past submissions (schema-safe).
    """
    cols = _table_columns(conn, "assignments")
    if not cols:
        return [], cols

    # Prefer user_id+week filters if those columns exist
    where = []
    params = []

    if "user_id" in cols:
        where.append("user_id = ?")
        params.append(user_id)
    elif "student_id" in cols:
        where.append("student_id = ?")
        params.append(user_id)

    if "week" in cols:
        where.append("week = ?")
        params.append(week)

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    order_col = "submitted_at" if "submitted_at" in cols else ("created_at" if "created_at" in cols else "id")
    sql = f"SELECT * FROM assignments{where_sql} ORDER BY {order_col} DESC"

    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        # Convert sqlite rows to dicts safely
        out = []
        for r in rows:
            try:
                out.append(dict(r))
            except Exception:
                # fallback if row isn't mapping-like
                out.append({f"col_{i}": r[i] for i in range(len(r))})
        return out, cols
    except Exception:
        return [], cols


def student_router(user):
    st.title("🎓 AI Essentials — Student Dashboard")

    user_id = user["id"]
    username = user.get("username", "student")

    progress = get_progress(user_id)

    # =================================================
    # COURSE PROGRESS GRID
    # =================================================
    st.subheader("📘 Course Progress")

    cols = st.columns(3)

    for week in range(1, TOTAL_WEEKS + 1):
        status = progress.get(week, "locked")

        label = f"Week {week}"
        if status == "completed":
            label += " ✔️"
        elif status == "unlocked":
            label += " 🔓"
        else:
            label += " 🔒"

        with cols[(week - 1) % 3]:
            # ---------- WEEK BUTTON ----------
            if status != "locked":
                if st.button(label, key=f"week_btn_{week}"):
                    st.session_state["selected_week"] = week
                    st.rerun()
            else:
                st.button(label, disabled=True, key=f"week_btn_locked_{week}")

            # ---------- WEEK PROGRESS BAR ----------
            if status == "completed":
                st.progress(1.0)
                st.caption("Completed")
            elif status == "unlocked":
                st.progress(0.5)
                st.caption("In Progress")
            else:
                st.progress(0.0)
                st.caption("Locked")

    # =================================================
    # DISPLAY WEEK CONTENT + ASSIGNMENT UPLOAD
    # =================================================
    if "selected_week" in st.session_state:
        week = st.session_state["selected_week"]

        st.divider()
        st.subheader(f"📖 Week {week} Content")

        file_path = os.path.join(CONTENT_DIR, f"week{week}.md")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                st.markdown(f.read())
        else:
            st.warning("Content not yet uploaded for this week.")

        # ---------- ASSIGNMENT UPLOAD (RESTORED) ----------
        st.divider()
        st.subheader(f"📤 Assignment Submission (Week {week})")

        st.caption("Upload your assignment file and click **Submit Assignment**.")

        uploaded = st.file_uploader(
            "Choose file (PDF/DOCX/PNG/JPG)",
            type=["pdf", "docx", "png", "jpg", "jpeg"],
            key=f"assignment_upload_week_{week}",
        )

        col_a, col_b = st.columns([1, 1])
        with col_a:
            submit_clicked = st.button("✅ Submit Assignment", key=f"submit_assignment_{week}")
        with col_b:
            clear_clicked = st.button("🧹 Clear Selected File", key=f"clear_assignment_file_{week}")

        if clear_clicked:
            # Reset uploader by rerun with a new key seed
            st.session_state[f"assignment_upload_week_{week}"] = None
            st.rerun()

        if submit_clicked:
            if uploaded is None:
                st.error("Please upload a file before submitting.")
            else:
                # Save file to disk
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = _safe_filename(uploaded.name)
                save_dir = os.path.join(ASSIGNMENTS_UPLOAD_ROOT, str(user_id), f"week{week}")
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, f"{ts}_{safe_name}")

                try:
                    with open(save_path, "wb") as out:
                        out.write(uploaded.getbuffer())

                    # Insert row into DB (schema-safe)
                    with read_conn() as conn:
                        assignment_cols = _table_columns(conn, "assignments")

                        payload = {
                            # user identifiers
                            "user_id": user_id,
                            "student_id": user_id,
                            "username": username,
                            "student_username": username,

                            # week + file info
                            "week": week,
                            "file_path": save_path,
                            "path": save_path,
                            "filename": safe_name,
                            "file_name": safe_name,

                            # timestamps
                            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

                            # status
                            "status": "submitted",
                        }

                        _insert_assignment_row(conn, assignment_cols, payload)

                    st.success("✅ Assignment submitted successfully.")
                    st.rerun()

                except Exception as e:
                    st.error(f"Submission failed: {e}")

        # Show past submissions for this week (if any)
        with read_conn() as conn:
            existing, _cols = _fetch_assignments(conn, user_id, week)

        if existing:
            st.markdown("#### 📄 Your previous submissions (this week)")
            # show a small, clean view
            for row in existing[:5]:
                rid = row.get("id", "—")
                status = row.get("status", "—")
                submitted_at = row.get("submitted_at") or row.get("created_at") or "—"
                fname = row.get("filename") or row.get("file_name") or row.get("path") or row.get("file_path") or "—"

                with st.expander(f"Submission #{rid} • {status} • {submitted_at}"):
                    st.write("**File:**", fname)
                    if row.get("admin_feedback"):
                        st.write("**Feedback:**", row.get("admin_feedback"))
                    if row.get("score") is not None:
                        st.write("**Score:**", row.get("score"))

        # ---------- MARK COMPLETED ----------
        if st.button("Mark Week as Completed", key=f"complete_week_{week}"):
            mark_week_completed(user_id, week)
            st.success(f"Week {week} marked as completed")
            st.rerun()

    # =================================================
    # FINAL EXAM
    # =================================================
    st.divider()
    st.subheader("📝 Final Exam")

    if "show_final_exam" not in st.session_state:
        st.session_state["show_final_exam"] = False

    with read_conn() as conn:
        row = conn.execute(
            """
            SELECT exam_unlocked, exam_reviewed
            FROM student_exam_status
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if not row or not row["exam_unlocked"]:
        st.warning("Final exam will be unlocked by the administrator after Week 6 completion.")
    else:
        if row["exam_reviewed"]:
            st.error("You have already reviewed the exam answers. Exam locked.")
        else:
            st.success("Final exam unlocked. You can start the exam.")
            if st.button("Start Final Exam", key="start_final_exam_btn"):
                st.session_state["show_final_exam"] = True
                st.rerun()

    if st.session_state.get("show_final_exam", False):
        from modules.week6_final_exam import show_exam
        show_exam(user)
        return

    # =================================================
    # CERTIFICATE
    # =================================================
    st.divider()
    st.subheader("🎖 Certificate")

    if has_certificate(user_id):
        st.success("Certificate issued")
    else:
        if can_issue_certificate(user_id):
            if st.button("Generate Certificate", key="generate_certificate"):
                issue_certificate(user_id)
                st.success("Certificate generated")

    # =================================================
    # SIDEBAR
    # =================================================
    with st.sidebar:
        st.markdown("### 👩‍🎓 Student Menu")
        st.markdown(user.get("username", ""))

        completed = sum(1 for s in progress.values() if s == "completed")
        st.progress(completed / TOTAL_WEEKS)
        st.caption(f"{completed} of {TOTAL_WEEKS} weeks completed")

        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
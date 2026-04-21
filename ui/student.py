import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

from services.db import read_conn
from services.progress import get_progress, mark_week_completed
from services.assignments import can_issue_certificate
from services.certificates import has_certificate, issue_certificate
from ui.support import support_page  # student help & support page


CONTENT_DIR = "content"
TOTAL_WEEKS = 6

# Where uploaded assignment files are stored (server)
ASSIGNMENTS_UPLOAD_ROOT = "/app/data/uploads/assignments"


def _safe_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^\w\-. ]+", "", name)
    name = name.replace(" ", "_")
    return name or "assignment_file"


def _table_columns(conn, table_name: str) -> set[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {r[1] if isinstance(r, (tuple, list)) else r["name"] for r in rows}
    except Exception:
        return set()


def _upsert_assignment_row(conn, cols: set[str], payload: dict) -> None:
    usable = {k: v for k, v in payload.items() if k in cols}
    if not usable:
        raise RuntimeError("Assignments table schema did not match expected fields.")

    has_user_id = "user_id" in usable and "user_id" in cols
    has_week = "week" in usable and "week" in cols

    if has_user_id and has_week:
        keys = list(usable.keys())
        placeholders = ", ".join(["?"] * len(keys))

        update_keys = [k for k in keys if k not in {"user_id", "week"}]
        if update_keys:
            update_clause = ", ".join([f"{k}=excluded.{k}" for k in update_keys])
            sql = f"""
                INSERT INTO assignments ({', '.join(keys)})
                VALUES ({placeholders})
                ON CONFLICT(user_id, week)
                DO UPDATE SET {update_clause}
            """
        else:
            sql = f"""
                INSERT INTO assignments ({', '.join(keys)})
                VALUES ({placeholders})
                ON CONFLICT(user_id, week)
                DO NOTHING
            """

        conn.execute(sql, tuple(usable[k] for k in keys))
        conn.commit()
        return

    # fallback delete+insert
    where = []
    params = []

    if "user_id" in usable and "user_id" in cols:
        where.append("user_id = ?")
        params.append(usable["user_id"])
    elif "student_id" in usable and "student_id" in cols:
        where.append("student_id = ?")
        params.append(usable["student_id"])

    if "week" in usable and "week" in cols:
        where.append("week = ?")
        params.append(usable["week"])

    if where:
        conn.execute(f"DELETE FROM assignments WHERE {' AND '.join(where)}", tuple(params))

    keys = list(usable.keys())
    placeholders = ", ".join(["?"] * len(keys))
    sql = f"INSERT INTO assignments ({', '.join(keys)}) VALUES ({placeholders})"
    conn.execute(sql, tuple(usable[k] for k in keys))
    conn.commit()


def _extract_grade(row: dict):
    g = row.get("grade")
    if g is None:
        g = row.get("score")
    return g


def _extract_feedback(row: dict):
    fb = row.get("feedback")
    if not fb:
        fb = row.get("admin_feedback")
    return fb


def _fetch_all_assignments_for_student(conn, user_id: str):
    cols = _table_columns(conn, "assignments")
    if not cols:
        return [], cols

    where = []
    params = []

    if "user_id" in cols:
        where.append("user_id = ?")
        params.append(user_id)
    elif "student_id" in cols:
        where.append("student_id = ?")
        params.append(user_id)

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    order_col = "week" if "week" in cols else ("submitted_at" if "submitted_at" in cols else "id")

    sql = f"SELECT * FROM assignments{where_sql} ORDER BY {order_col} ASC"
    rows = conn.execute(sql, tuple(params)).fetchall()

    out = []
    for r in rows:
        try:
            out.append(dict(r))
        except Exception:
            out.append({f"col_{i}": r[i] for i in range(len(r))})
    return out, cols


def student_router(user):
    st.title("🎓 AI Essentials — Student Dashboard")

    user_id = user["id"]
    username = user.get("username", "student")

    # ------------------------------
    # Support page routing
    # ------------------------------
    if st.session_state.get("page") == "support":
        st.markdown("### 🆘 Help & Support")
        if st.button("⬅️ Return to Dashboard", key="student_support_back_btn"):
            st.session_state["page"] = None
            st.rerun()
        support_page(user)
        return

    progress = get_progress(user_id)

    # =================================================
    # RESTORED: GRADES OVERVIEW (SCORES PER WEEK)
    # =================================================
    st.subheader("📊 My Grades (All Weeks)")
    with read_conn() as conn:
        all_rows, _cols = _fetch_all_assignments_for_student(conn, user_id)

    rows_by_week = {}
    for r in all_rows:
        wk = r.get("week")
        if wk is None:
            continue
        rows_by_week.setdefault(int(wk), []).append(r)

    week_summary = []
    for wk in range(1, TOTAL_WEEKS + 1):
        submissions = rows_by_week.get(wk, [])
        latest = None
        if submissions:

            def _sort_key(x):
                return (x.get("submitted_at") or x.get("created_at") or "", x.get("id") or 0)

            latest = sorted(submissions, key=_sort_key, reverse=True)[0]

        grade = _extract_grade(latest) if latest else None
        status = (latest.get("status") if latest else None) or ("submitted" if latest else "not submitted")
        submitted_at = (latest.get("submitted_at") or latest.get("created_at")) if latest else "—"
        fb = _extract_feedback(latest) if latest else ""

        week_summary.append(
            {
                "Week": wk,
                "Submitted": "Yes" if latest else "No",
                "Status": status,
                "Score/Grade": grade if grade is not None else "—",
                "Submitted At": submitted_at,
                "Feedback (short)": (fb[:60] + "…") if fb and len(fb) > 60 else (fb or "—"),
            }
        )

    st.dataframe(pd.DataFrame(week_summary), use_container_width=True)

    # =================================================
    # COURSE PROGRESS GRID
    # =================================================
    st.subheader("📘 Course Progress")

    # ✅ Week 0 (Orientation) — always available (put it first)
    if st.button("Week 0 (Orientation) 🔓", key="week0_btn"):
        st.session_state["selected_week"] = 0
        st.rerun()

    grid_cols = st.columns(3)
    for week in range(1, TOTAL_WEEKS + 1):
        status = progress.get(week, "locked")

        label = f"Week {week}"
        if status == "completed":
            label += " ✔️"
        elif status == "unlocked":
            label += " 🔓"
        else:
            label += " 🔒"

        with grid_cols[(week - 1) % 3]:
            if status != "locked":
                if st.button(label, key=f"week_btn_{week}"):
                    st.session_state["selected_week"] = week
                    st.rerun()
            else:
                st.button(label, disabled=True, key=f"week_btn_locked_{week}")

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
    # DISPLAY WEEK CONTENT + ASSIGNMENT UPLOAD + WEEK DETAIL (WITH GRADE)
    # =================================================
    if "selected_week" in st.session_state:
        week = st.session_state["selected_week"]

        st.divider()
        st.subheader(f"📖 Week {week} Content")

        if week == 0:
            file_path = os.path.join(CONTENT_DIR, "week0.md")
        else:
            file_path = os.path.join(CONTENT_DIR, f"week{week}.md")

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                st.markdown(f.read())
        else:
            st.warning("Content not yet uploaded for this week.")

        # ✅ Week 0: no assignment, no completion marking
        if week == 0:
            st.info("Orientation week does not require assignment submission.")
        else:
            # ---------- ASSIGNMENT UPLOAD ----------
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
                st.session_state[f"assignment_upload_week_{week}"] = None
                st.rerun()

            if submit_clicked:
                if uploaded is None:
                    st.error("Please upload a file before submitting.")
                else:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = _safe_filename(uploaded.name)
                    save_dir = os.path.join(ASSIGNMENTS_UPLOAD_ROOT, str(user_id), f"week{week}")
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, f"{ts}_{safe_name}")

                    try:
                        with open(save_path, "wb") as out:
                            out.write(uploaded.getbuffer())

                        with read_conn() as conn:
                            assignment_cols = _table_columns(conn, "assignments")
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                            payload = {
                                "user_id": user_id,
                                "student_id": user_id,
                                "username": username,
                                "student_username": username,
                                "week": week,
                                "file_path": save_path,
                                "path": save_path,
                                "filename": safe_name,
                                "file_name": safe_name,
                                "original_filename": safe_name,
                                "submitted_at": now_str,
                                "created_at": now_str,
                                "status": "submitted",
                            }

                            _upsert_assignment_row(conn, assignment_cols, payload)

                        st.success("✅ Assignment submitted successfully.")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Submission failed: {e}")

            # ---------- SHOW THIS WEEK SUBMISSION + GRADE/FEEDBACK ----------
            st.divider()
            st.subheader(f"✅ Week {week} Grade & Feedback")

            latest = None
            submissions = rows_by_week.get(week, [])
            if submissions:

                def _sort_key(x):
                    return (x.get("submitted_at") or x.get("created_at") or "", x.get("id") or 0)

                latest = sorted(submissions, key=_sort_key, reverse=True)[0]

            if not latest:
                st.info("No submission yet for this week.")
            else:
                grade = _extract_grade(latest)
                fb = _extract_feedback(latest)
                submitted_at = latest.get("submitted_at") or latest.get("created_at") or "—"

                st.write(f"**Submitted At:** {submitted_at}")
                if grade is not None:
                    st.success(f"**Score/Grade:** {grade}")
                else:
                    st.warning("Score/Grade not yet released.")

                if fb:
                    st.info(f"**Feedback:** {fb}")
                else:
                    st.caption("No feedback yet.")

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
    # CERTIFICATE (DOWNLOAD + AUTO-RESOLVE PATH + REGENERATE)
    # =================================================
    st.divider()
    st.subheader("🎖 Certificate")

    def _get_certificate_row(conn, uid):
        cols = [r[1] for r in conn.execute("PRAGMA table_info(certificates)").fetchall()]
        if not cols:
            return None

        user_col = "user_id" if "user_id" in cols else ("student_id" if "student_id" in cols else None)
        if not user_col:
            return None

        order_col = "issued_at" if "issued_at" in cols else ("created_at" if "created_at" in cols else ("id" if "id" in cols else None))
        order_sql = f" ORDER BY {order_col} DESC" if order_col else ""

        row = conn.execute(
            f"SELECT * FROM certificates WHERE {user_col}=?{order_sql} LIMIT 1",
            (uid,),
        ).fetchone()

        return dict(row) if row else None

    def _resolve_certificate_path(raw_path: str):
        if not raw_path:
            return None

        raw_path = str(raw_path).strip()
        base = os.path.basename(raw_path)

        candidates = [
            raw_path,
            os.path.join("/app/data", raw_path),
            os.path.join("/app/data/generated_certificates", base),
            os.path.join("/app/data/certificates", base),
            os.path.join(os.getcwd(), raw_path),
            os.path.join(os.getcwd(), "generated_certificates", base),
        ]

        for p in candidates:
            p_abs = os.path.abspath(p)
            if os.path.exists(p_abs):
                return p_abs

        return None

    def _get_full_name():
        return (
            user.get("full_name")
            or user.get("name")
            or user.get("username")
            or "Student"
        )

    if has_certificate(user_id):
        st.success("Certificate issued")

        cert_row = None
        raw_path = None
        resolved_path = None

        try:
            with read_conn() as conn:
                cert_row = _get_certificate_row(conn, user_id)

            if cert_row:
                for k in ["file_path", "certificate_path", "path", "pdf_path"]:
                    if cert_row.get(k):
                        raw_path = cert_row.get(k)
                        break

            resolved_path = _resolve_certificate_path(raw_path) if raw_path else None

        except Exception:
            cert_row = None

        if resolved_path:
            with open(resolved_path, "rb") as f:
                st.download_button(
                    "⬇️ Download Certificate (PDF)",
                    data=f.read(),
                    file_name=f"Chumcred_Certificate_{user.get('username','student')}.pdf",
                    mime="application/pdf",
                    key="download_certificate_btn",
                )
        else:
            st.warning("Certificate record exists, but the certificate file was not found on the server.")
            if raw_path:
                st.code(str(raw_path))

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🔁 Regenerate Certificate", key="regen_certificate_btn"):
                    issue_certificate(user_id, _get_full_name())
                    st.success("Certificate regenerated. Reloading…")
                    st.rerun()
            with col2:
                st.info("If this persists, confirm Railway has a Volume mounted to /app/data.")

    else:
        if can_issue_certificate(user_id):
            if st.button("Generate Certificate", key="generate_certificate"):
                issue_certificate(user_id, _get_full_name())
                st.success("Certificate generated")
                st.rerun()

    # =================================================
    # SIDEBAR
    # =================================================
    with st.sidebar:
        st.markdown("### 👩‍🎓 Student Menu")
        st.markdown(username)

        # Count ONLY Weeks 1–6 (ignore Week 0 and any stray keys)
        completed = 0
        for wk in range(1, TOTAL_WEEKS + 1):
            if progress.get(wk) == "completed":
                completed += 1

        ratio = completed / TOTAL_WEEKS
        ratio = max(0.0, min(1.0, ratio))

        st.progress(ratio)
        st.caption(f"{completed} of {TOTAL_WEEKS} weeks completed")

        if st.button("Week 0 (Orientation)", key="week0_btn_sidebar"):
            st.session_state["selected_week"] = 0
            st.rerun()

        if st.button("🆘 Help & Support", key="student_help_support_btn"):
            st.session_state["page"] = "support"
            st.rerun()

        if st.button("🚪 Logout", key="student_logout_btn"):
            st.session_state.clear()
            st.rerun()
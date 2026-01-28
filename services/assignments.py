
# services/assignments.py
# --------------------------------------------------
# services/assignments.py
# --------------------------------------------------
import os
from datetime import datetime

from services.db import read_conn, write_txn

# ==================================================
# CONFIG
# ==================================================
UPLOAD_ROOT = os.getenv("LMS_UPLOAD_PATH", "/app/data/uploads")
ASSIGNMENT_DIR = os.path.join(UPLOAD_ROOT, "assignments")

print("📌 ASSIGNMENTS DB:", os.getenv("LMS_DB_PATH"))
print("📌 ASSIGNMENTS UPLOAD:", UPLOAD_ROOT)


# ==================================================
# HELPERS
# ==================================================
def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _ensure_user_dir(user_id: int) -> str:
    user_dir = os.path.join(ASSIGNMENT_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def _assignment_filename(week: int) -> str:
    return f"week_{int(week)}.pdf"


# ==================================================
# CORE FUNCTIONS
# ==================================================
def save_assignment(user_id: int, week: int, uploaded_file) -> None:
    """
    Save uploaded PDF to disk and upsert submission row in DB.
    IMPORTANT: If DB insert fails, raise a clear exception (no silent failure).
    """
    if uploaded_file is None:
        raise ValueError("No file uploaded.")

    week = int(week)
    user_id = int(user_id)

    # Ensure folders exist
    os.makedirs(ASSIGNMENT_DIR, exist_ok=True)
    user_dir = _ensure_user_dir(user_id)

    filename = _assignment_filename(week)
    file_path = os.path.join(user_dir, filename)

    # Write file
    try:
        data = uploaded_file.getbuffer()
        with open(file_path, "wb") as f:
            f.write(data)
    except Exception as e:
        raise RuntimeError(f"Failed to write uploaded file to disk: {e}") from e

    submitted_at = _now_iso()
    original_filename = getattr(uploaded_file, "name", None)

    # Upsert DB row
    try:
        with write_txn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO assignments (
                    user_id, week, file_path, submitted_at, original_filename,
                    status, grade, feedback, reviewed_at, reviewed_by
                )
                VALUES (?, ?, ?, ?, ?, 'submitted', NULL, NULL, NULL, NULL)
                ON CONFLICT(user_id, week)
                DO UPDATE SET
                    file_path=excluded.file_path,
                    submitted_at=excluded.submitted_at,
                    original_filename=excluded.original_filename,
                    status='submitted',
                    grade=NULL,
                    feedback=NULL,
                    reviewed_at=NULL,
                    reviewed_by=NULL
                """,
                (user_id, week, file_path, submitted_at, original_filename),
            )
    except Exception as e:
        raise RuntimeError(f"Failed to save assignment into DB: {e}") from e


def has_assignment(user_id: int, week: int) -> bool:
    user_id = int(user_id)
    week = int(week)
    with read_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM assignments WHERE user_id=? AND week=? LIMIT 1",
            (user_id, week),
        ).fetchone()
        return row is not None


def get_week_grade(user_id: int, week: int):
    """
    Returns (grade, badge) or (None, None)
    Badge is derived from grade %.
    """
    user_id = int(user_id)
    week = int(week)

    with read_conn() as conn:
        row = conn.execute(
            """
            SELECT grade, status
            FROM assignments
            WHERE user_id=? AND week=?
            LIMIT 1
            """,
            (user_id, week),
        ).fetchone()

    if not row:
        return None, None

    status = row["status"]
    grade = row["grade"]

    if status not in ("approved", "graded") or grade is None:
        return None, None

    grade_val = float(grade)
    badge = _grade_to_badge(grade_val)
    return grade_val, badge


def _grade_to_badge(grade: float) -> str:
    if grade >= 70:
        return "A"
    if grade >= 60:
        return "B"
    if grade >= 50:
        return "C"
    return "Fail"


def get_student_grade_summary(user_id: int):
    """
    Returns list of dicts:
    [{"week":1,"status":"graded"/"pending","grade":90,"badge":"A"}, ...]
    Weeks 1..6
    """
    user_id = int(user_id)

    # Weeks fixed to 6 as in student.py TOTAL_WEEKS=6
    weeks = list(range(1, 7))
    summary = []

    with read_conn() as conn:
        rows = conn.execute(
            """
            SELECT week, status, grade
            FROM assignments
            WHERE user_id=?
            """,
            (user_id,),
        ).fetchall()

    by_week = {}
    for r in rows:
        by_week[int(r["week"])] = {
            "status": r["status"],
            "grade": r["grade"],
        }

    for w in weeks:
        if w in by_week and by_week[w]["status"] in ("approved", "graded") and by_week[w]["grade"] is not None:
            g = float(by_week[w]["grade"])
            summary.append(
                {"week": w, "status": "graded", "grade": g, "badge": _grade_to_badge(g)}
            )
        else:
            summary.append({"week": w, "status": "pending", "grade": None, "badge": None})

    return summary


def list_all_assignments():
    """
    Used by admin review page.
    Returns rows with: id, user_id, username, week, file_path, submitted_at, status, grade, feedback
    """
    with read_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                a.id,
                a.user_id,
                u.username,
                a.week,
                a.file_path,
                a.submitted_at,
                a.original_filename,
                a.status,
                a.grade,
                a.feedback,
                a.reviewed_at,
                a.reviewed_by
            FROM assignments a
            JOIN users u ON u.id = a.user_id
            ORDER BY a.submitted_at DESC
            """
        ).fetchall()
        return rows


def list_student_assignments(user_id: int):
    """
    Handy for debugging and student views if needed later.
    """
    user_id = int(user_id)
    with read_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, week, file_path, submitted_at, status, grade, feedback
            FROM assignments
            WHERE user_id=?
            ORDER BY week ASC
            """,
            (user_id,),
        ).fetchall()
        return rows


def review_assignment(assignment_id: int, grade: float, feedback: str, reviewed_by: int = None):
    """
    Admin review action: mark as approved/graded and store grade.
    """
    assignment_id = int(assignment_id)
    grade_val = float(grade)
    reviewed_at = _now_iso()

    status = "approved"  # keep compatible with your current logic

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE assignments
            SET status=?,
                grade=?,
                feedback=?,
                reviewed_at=?,
                reviewed_by=?
            WHERE id=?
            """,
            (status, grade_val, feedback, reviewed_at, reviewed_by, assignment_id),
        )


def can_issue_certificate(user_id: int) -> bool:
    """
    Certificate only after all weeks 1..6 have approved/graded grades (non-null).
    """
    user_id = int(user_id)
    required_weeks = 6

    with read_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM assignments
            WHERE user_id=?
              AND status IN ('approved', 'graded')
              AND grade IS NOT NULL
            """,
            (user_id,),
        ).fetchone()

    cnt = int(row["cnt"]) if row else 0
    return cnt >= required_weeks

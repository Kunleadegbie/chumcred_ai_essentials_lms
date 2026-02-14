# ==================================================
# services/assignments.py
# ==================================================
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


def _grade_to_badge(grade: float) -> str:
    if grade >= 70:
        return "A"
    if grade >= 60:
        return "B"
    if grade >= 50:
        return "C"
    return "Fail"


# ==================================================
# CORE FUNCTIONS
# ==================================================
def save_assignment(user_id: int, week: int, uploaded_file) -> None:
    if uploaded_file is None:
        raise ValueError("No file uploaded.")

    week = int(week)
    user_id = int(user_id)

    os.makedirs(ASSIGNMENT_DIR, exist_ok=True)
    user_dir = _ensure_user_dir(user_id)

    filename = _assignment_filename(week)
    file_path = os.path.join(user_dir, filename)

    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    except Exception as e:
        raise RuntimeError(f"Failed to write uploaded file: {e}") from e

    submitted_at = _now_iso()
    original_filename = getattr(uploaded_file, "name", None)

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


def has_assignment(user_id: int, week: int) -> bool:
    with read_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM assignments WHERE user_id=? AND week=? LIMIT 1",
            (int(user_id), int(week)),
        ).fetchone()
        return row is not None


def get_week_grade(user_id: int, week: int):
    with read_conn() as conn:
        row = conn.execute(
            """
            SELECT grade, status
            FROM assignments
            WHERE user_id=? AND week=?
            LIMIT 1
            """,
            (int(user_id), int(week)),
        ).fetchone()

    if not row:
        return None, None

    if row["status"] not in ("approved", "graded") or row["grade"] is None:
        return None, None

    grade_val = float(row["grade"])
    return grade_val, _grade_to_badge(grade_val)


# ==================================================
# 🔥 UPDATED FUNCTION (FEEDBACK FIX)
# ==================================================
def get_student_grade_summary(user_id: int):
    """
    Returns list of dicts:
    [
      {"week":1,"status":"graded","grade":90,"badge":"A","feedback":"Very good"},
      ...
    ]
    """

    user_id = int(user_id)
    weeks = list(range(1, 7))
    summary = []

    with read_conn() as conn:
        rows = conn.execute(
            """
            SELECT week, status, grade, feedback
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
            "feedback": r["feedback"],
        }

    for w in weeks:
        if (
            w in by_week
            and by_week[w]["status"] in ("approved", "graded")
            and by_week[w]["grade"] is not None
        ):
            g = float(by_week[w]["grade"])
            summary.append(
                {
                    "week": w,
                    "status": "graded",
                    "grade": g,
                    "badge": _grade_to_badge(g),
                    "feedback": by_week[w]["feedback"],
                }
            )
        else:
            summary.append(
                {
                    "week": w,
                    "status": "pending",
                    "grade": None,
                    "badge": None,
                    "feedback": None,
                }
            )

    return summary


def list_all_assignments():
    with read_conn() as conn:
        return conn.execute(
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


def list_student_assignments(user_id: int):
    with read_conn() as conn:
        return conn.execute(
            """
            SELECT id, user_id, week, file_path, submitted_at,
                   status, grade, feedback
            FROM assignments
            WHERE user_id=?
            ORDER BY week ASC
            """,
            (int(user_id),),
        ).fetchall()


def review_assignment(assignment_id: int, grade: float, feedback: str, reviewed_by: int = None):
    with write_txn() as conn:
        conn.execute(
            """
            UPDATE assignments
            SET status='approved',
                grade=?,
                feedback=?,
                reviewed_at=?,
                reviewed_by=?
            WHERE id=?
            """,
            (
                float(grade),
                feedback,
                _now_iso(),
                reviewed_by,
                int(assignment_id),
            ),
        )


def can_issue_certificate(user_id: int) -> bool:
    with read_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM assignments
            WHERE user_id=?
              AND status IN ('approved','graded')
              AND grade IS NOT NULL
            """,
            (int(user_id),),
        ).fetchone()

    return int(row["cnt"]) >= 6 if row else False

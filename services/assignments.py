
# services/assignments.py
# services/assignments.py
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Tuple

from services.db import read_conn, write_txn

UPLOAD_DIR = os.getenv("LMS_UPLOAD_DIR", "uploads")


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


def _ensure_upload_dir() -> None:
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def grade_to_badge(score: Optional[int]) -> Optional[str]:
    """
    Option #2 badge mapping:
    Distinction / Merit / Pass / Fail
    """
    if score is None:
        return None
    if score >= 80:
        return "Distinction"
    if score >= 65:
        return "Merit"
    if score >= 50:
        return "Pass"
    return "Fail"


# -------------------------------------------------
# Student-side helpers
# -------------------------------------------------
def has_assignment(user_id: int, week: int) -> bool:
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM assignments WHERE user_id=? AND week=?",
            (user_id, week),
        )
        return cur.fetchone() is not None


def get_assignment_for_week(user_id: int, week: int):
    """
    Returns sqlite3.Row or None
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, week, file_path, submitted_at, status, grade, feedback, reviewed_at
            FROM assignments
            WHERE user_id = ? AND week = ?
            """,
            (user_id, week),
        )
        return cur.fetchone()


def get_student_grade_summary(user_id: int) -> dict:
    from services.db import read_conn

    summary = {"passed": 0, "merit": 0, "distinction": 0}

    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT grade
            FROM assignments
            WHERE user_id = ? AND status = 'approved'
            """,
            (user_id,),
        )
        rows = cur.fetchall()

    for r in rows:
        if r["grade"] == "Pass":
            summary["passed"] += 1
        elif r["grade"] == "Merit":
            summary["merit"] += 1
        elif r["grade"] == "Distinction":
            summary["distinction"] += 1

    return summary



def get_week_grade(user_id: int, week: int) -> Tuple[Optional[int], Optional[str]]:
    """
    Returns: (grade_percent, badge_label)
    Badge is computed from grade.
    """
    row = get_assignment_for_week(user_id, week)
    if not row:
        return None, None
    if row["grade"] is None:
        return None, None
    return int(row["grade"]), grade_to_badge(int(row["grade"]))


def get_grade_summary(user_id: int) -> dict:
    """
    Summary used for student dashboard tiles.
    Returns:
      {
        "graded_count": int,
        "avg_grade": float|None,
        "best_badge": str|None,
        "latest_grade": int|None,
        "latest_badge": str|None
      }
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT week, grade, status
            FROM assignments
            WHERE user_id = ? AND grade IS NOT NULL
            ORDER BY week ASC
            """,
            (user_id,),
        )
        rows = cur.fetchall()

    graded = [int(r["grade"]) for r in rows if r["grade"] is not None]
    if not graded:
        return {
            "graded_count": 0,
            "avg_grade": None,
            "best_badge": None,
            "latest_grade": None,
            "latest_badge": None,
        }

    avg = sum(graded) / len(graded)
    latest_grade = graded[-1]
    latest_badge = grade_to_badge(latest_grade)

    # best badge by highest grade
    best_grade = max(graded)
    best_badge = grade_to_badge(best_grade)

    return {
        "graded_count": len(graded),
        "avg_grade": avg,
        "best_badge": best_badge,
        "latest_grade": latest_grade,
        "latest_badge": latest_badge,
    }


# -------------------------------------------------
# Submission
# -------------------------------------------------
def save_assignment(user_id, week, file):

    import os
    import uuid
    from datetime import datetime

    conn = write_txn()
    cur = conn.cursor()

    # ===============================
    # Ensure upload directory exists
    # ===============================
    UPLOAD_DIR = "uploads/assignments"

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # ===============================
    # Generate safe filename
    # ===============================
    ext = os.path.splitext(file.name)[1]

    filename = f"{user_id}_week{week}_{uuid.uuid4().hex}{ext}"

    file_path = os.path.join(UPLOAD_DIR, filename)

    # ===============================
    # Save file to disk
    # ===============================
    try:
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

    except Exception as e:
        raise Exception(f"File save failed: {e}")

    # ===============================
    # Save to database
    # ===============================
    now = datetime.utcnow().isoformat()

    try:
        cur.execute(
            """
            INSERT INTO assignments (
                user_id,
                week,
                file_path,
                status,
                submitted_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                week,
                file_path,
                "submitted",
                now,
            ),
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise Exception(f"DB insert failed: {e}")

    finally:
        conn.close()


# -------------------------------------------------
# Admin helpers (needed by ui/admin.py)
# -------------------------------------------------
def list_all_assignments():
    """
    Returns all assignments for admin review.
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                a.id,
                a.user_id,
                u.username,
                a.week,
                a.file_path,
                a.status,
                a.grade,
                a.feedback,
                a.submitted_at,
                a.reviewed_at
            FROM assignments a
            JOIN users u ON u.id = a.user_id
            ORDER BY a.submitted_at DESC
            """
        )
        return cur.fetchall()


def review_assignment(assignment_id: int, grade: int, feedback: str = "", status: str = "reviewed") -> None:
    """
    Admin sets grade + feedback.
    Keeps status flexible:
      - "reviewed" (graded but not final)
      - "approved" (final)
    """
    grade_int = int(grade)

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE assignments
            SET grade = ?, feedback = ?, status = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (grade_int, feedback, status, _utcnow_iso(), int(assignment_id)),
        )

# --------------------------------------------------
# CERTIFICATE ELIGIBILITY CHECK
# --------------------------------------------------
def can_issue_certificate(user_id: int) -> bool:
    """
    Returns True only if ALL weeks (1–6) are graded.
    """

    from services.db import read_conn

    TOTAL_WEEKS = 6

    with read_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COUNT(*) AS graded_count
            FROM assignments
            WHERE user_id = ?
              AND status = 'approved'
            """,
            (user_id,),
        )

        row = cur.fetchone()
        graded = row["graded_count"] if row else 0

    return graded >= TOTAL_WEEKS

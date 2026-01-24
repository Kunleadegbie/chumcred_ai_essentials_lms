
# services/assignments.py
# services/assignments.py
import os
from datetime import datetime
from typing import List

from services.db import read_conn, write_txn

UPLOAD_DIR = "uploads/assignments"


def _ensure_upload_dir():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================================================
# STUDENT FUNCTIONS
# =========================================================

def save_assignment(user_id: int, week: int, uploaded_file):
    """
    Save or overwrite a student's assignment for a given week.
    """
    _ensure_upload_dir()

    filename = f"user_{user_id}_week_{week}.pdf"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO assignments (user_id, week, file_path, submitted_at, status)
            VALUES (?, ?, ?, ?, 'submitted')
            ON CONFLICT(user_id, week)
            DO UPDATE SET
                file_path = excluded.file_path,
                submitted_at = excluded.submitted_at,
                status = 'submitted',
                grade = NULL,
                feedback = NULL,
                reviewed_at = NULL
            """,
            (user_id, week, path, now),
        )


def has_assignment(user_id: int, week: int) -> bool:
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM assignments WHERE user_id=? AND week=?",
            (user_id, week),
        )
        return cur.fetchone() is not None


def list_student_assignments(user_id: int) -> List[dict]:
    """
    Used by student dashboard to show grades.
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                week,
                status,
                grade,
                feedback,
                submitted_at,
                reviewed_at
            FROM assignments
            WHERE user_id=?
            ORDER BY week
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_assignment_for_week(user_id: int, week: int) -> dict | None:
    """
    Returns a single assignment row as dict for a user & week.
    Used by student dashboard.
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM assignments
            WHERE user_id=? AND week=?
            """,
            (user_id, week),
        )
        row = cur.fetchone()
        return dict(row) if row else None


# =========================================================
# ADMIN FUNCTIONS
# =========================================================

def list_all_assignments() -> List[dict]:
    """
    Used by Admin Assignment Review UI
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
                a.submitted_at,
                a.status,
                a.grade,
                a.feedback
            FROM assignments a
            JOIN users u ON u.id = a.user_id
            ORDER BY a.submitted_at DESC
            """
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def review_assignment(assignment_id: int, grade: int, feedback: str | None = None):
    """
    Admin grades an assignment.
    """
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE assignments
            SET
                grade=?,
                feedback=?,
                status='graded',
                reviewed_at=?
            WHERE id=?
            """,
            (grade, feedback, now, assignment_id),
        )


def get_week_grade(user_id: int, week: int) -> int | None:
    """
    Returns numeric grade for a specific week.
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT grade
            FROM assignments
            WHERE user_id=? AND week=?
            """,
            (user_id, week),
        )
        row = cur.fetchone()

    return row["grade"] if row and row["grade"] is not None else None


# =========================================================
# GRADE BADGE (SINGLE SOURCE OF TRUTH)
# =========================================================

def get_grade_badge(score: int | None):
    """
    Convert numeric score into grade badge.
    Option #2: Pass / Merit / Distinction.
    """

    if score is None:
        return {"label": "Pending", "color": "gray", "passed": False}

    try:
        score = int(score)
    except (ValueError, TypeError):
        return {"label": "Invalid", "color": "gray", "passed": False}

    if score >= 70:
        return {"label": "Distinction", "color": "purple", "passed": True}
    elif score >= 60:
        return {"label": "Merit", "color": "blue", "passed": True}
    elif score >= 50:
        return {"label": "Pass", "color": "green", "passed": True}
    else:
        return {"label": "Fail", "color": "red", "passed": False}

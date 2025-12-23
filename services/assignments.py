
# services/assignments.py
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from services.db import get_conn

TOTAL_WEEKS = 6

# Project root = one level above /services
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "assignments")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ------------------------------------------------------
# Schema management (self-healing)
# ------------------------------------------------------
def ensure_assignments_schema() -> None:
    """
    Ensures assignments table exists and contains expected columns.
    This prevents "no such column: status" across old DBs.
    """
    conn = get_conn()
    cur = conn.cursor()

    # 1) Create table (latest schema)
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

    # 2) Add missing columns for older DBs
    cur.execute("PRAGMA table_info(assignments)")
    existing_cols = {row[1] for row in cur.fetchall()}

    def add_col(col_sql: str) -> None:
        cur.execute(f"ALTER TABLE assignments ADD COLUMN {col_sql}")

    # Backward-compat columns
    if "original_filename" not in existing_cols:
        add_col("original_filename TEXT")
    if "status" not in existing_cols:
        add_col("status TEXT NOT NULL DEFAULT 'submitted'")
    if "grade" not in existing_cols:
        add_col("grade REAL")
    if "feedback" not in existing_cols:
        add_col("feedback TEXT")
    if "reviewed_at" not in existing_cols:
        add_col("reviewed_at TEXT")
    if "reviewed_by" not in existing_cols:
        add_col("reviewed_by INTEGER")

    conn.commit()
    conn.close()


# Call once on import (safe)
ensure_assignments_schema()


# ------------------------------------------------------
# File helpers
# ------------------------------------------------------
def _assignment_path(user_id: int, week: int) -> str:
    user_dir = os.path.join(UPLOAD_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, f"week_{week}.pdf")


# ------------------------------------------------------
# Core functions used by UI
# ------------------------------------------------------
def save_assignment(user_id: int, week: int, uploaded_file) -> str:
    """
    Saves uploaded assignment PDF and upserts DB row.
    Returns saved file_path.
    """
    ensure_assignments_schema()

    file_path = _assignment_path(user_id, week)
    original_filename = getattr(uploaded_file, "name", None)

    # Write file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    conn = get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()

    # Upsert by (user_id, week)
    cur.execute(
        """
        INSERT INTO assignments (user_id, week, file_path, original_filename, submitted_at, status)
        VALUES (?, ?, ?, ?, ?, 'submitted')
        ON CONFLICT(user_id, week) DO UPDATE SET
            file_path=excluded.file_path,
            original_filename=excluded.original_filename,
            submitted_at=excluded.submitted_at,
            status='submitted',
            grade=NULL,
            feedback=NULL,
            reviewed_at=NULL,
            reviewed_by=NULL
        """,
        (user_id, week, file_path, original_filename, now),
    )

    conn.commit()
    conn.close()
    return file_path


def has_assignment(user_id: int, week: int) -> bool:
    ensure_assignments_schema()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM assignments WHERE user_id=? AND week=? LIMIT 1",
        (user_id, week),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def get_assignment(user_id: int, week: int) -> Optional[Dict[str, Any]]:
    ensure_assignments_schema()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, file_path, original_filename, submitted_at, status, grade, feedback, reviewed_at, reviewed_by
        FROM assignments
        WHERE user_id=? AND week=?
        """,
        (user_id, week),
    )
    r = cur.fetchone()
    conn.close()
    if not r:
        return None

    return {
        "id": r[0],
        "file_path": r[1],
        "original_filename": r[2],
        "submitted_at": r[3],
        "status": r[4],
        "grade": r[5],
        "feedback": r[6],
        "reviewed_at": r[7],
        "reviewed_by": r[8],
        "week": week,
        "user_id": user_id,
    }


def list_student_assignments(user_id: int) -> List[Dict[str, Any]]:
    """
    Used by student UI to show submission + grade per week.
    """
    ensure_assignments_schema()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT week, file_path, original_filename, submitted_at, status, grade, feedback, reviewed_at
        FROM assignments
        WHERE user_id=?
        ORDER BY week
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        out.append(
            {
                "week": r[0],
                "file_path": r[1],
                "original_filename": r[2],
                "submitted_at": r[3],
                "status": r[4],
                "grade": r[5],
                "feedback": r[6],
                "reviewed_at": r[7],
            }
        )
    return out


# ------------------------------------------------------
# Admin review helpers
# ------------------------------------------------------
def list_assignments_for_review(status: str = "submitted") -> List[Dict[str, Any]]:
    """
    Returns assignments by status (default: submitted).
    """
    ensure_assignments_schema()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.id, a.user_id, a.week, a.file_path, a.original_filename, a.submitted_at, a.status, a.grade
        FROM assignments a
        WHERE a.status=?
        ORDER BY a.submitted_at DESC
        """,
        (status,),
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "user_id": r[1],
            "week": r[2],
            "file_path": r[3],
            "original_filename": r[4],
            "submitted_at": r[5],
            "status": r[6],
            "grade": r[7],
        }
        for r in rows
    ]


def review_assignment(
    assignment_id: int,
    decision: str,  # approved | rejected
    grade: Optional[float] = None,
    feedback: Optional[str] = None,
    reviewed_by: Optional[int] = None,
) -> None:
    """
    Saves admin decision + grade.
    NOTE: your progress completion should be driven by admin approval (not student submission).
    """
    ensure_assignments_schema()

    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected'")

    conn = get_conn()
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
        (
            decision,
            grade,
            feedback,
            datetime.utcnow().isoformat(),
            reviewed_by,
            assignment_id,
        ),
    )
    conn.commit()
    conn.close()

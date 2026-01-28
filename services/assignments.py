
# services/assignments.py
# --------------------------------------------------
# services/assignments.py
# --------------------------------------------------

import os
import sqlite3
from datetime import datetime

from services.db import read_conn, write_txn


# ==================================================
# DEBUG
# ==================================================

print("📌 ASSIGNMENTS DB:", os.getenv("LMS_DB_PATH"))
print("📌 ASSIGNMENTS UPLOAD:", os.getenv("LMS_UPLOAD_PATH"))


# ==================================================
# CONFIG
# ==================================================

UPLOAD_ROOT = os.getenv(
    "LMS_UPLOAD_PATH",
    "/app/data/uploads"
)

ASSIGNMENT_DIR = os.path.join(UPLOAD_ROOT, "assignments")


# ==================================================
# SAVE ASSIGNMENT
# ==================================================

def save_assignment(user_id, week, uploaded_file):

    # Ensure folders exist
    os.makedirs(ASSIGNMENT_DIR, exist_ok=True)

    user_dir = os.path.join(ASSIGNMENT_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    # File path
    file_path = os.path.join(user_dir, f"week_{week}.pdf")

    # -----------------------------
    # Save File
    # -----------------------------
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    now = datetime.utcnow().isoformat()

    # -----------------------------
    # Save DB Record
    # -----------------------------
    with write_txn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO assignments (
                user_id,
                week,
                file_path,
                status,
                submitted_at
            )
            VALUES (?, ?, ?, 'submitted', ?)
            ON CONFLICT(user_id, week)
            DO UPDATE SET
                file_path=excluded.file_path,
                status='submitted',
                submitted_at=excluded.submitted_at
            """,
            (user_id, week, file_path, now),
        )


# ==================================================
# CHECK IF ASSIGNMENT EXISTS
# ==================================================

def has_assignment(user_id: int, week: int) -> bool:

    with read_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 1
            FROM assignments
            WHERE user_id=? AND week=? AND file_path IS NOT NULL
            LIMIT 1
            """,
            (user_id, week),
        )

        return cur.fetchone() is not None


# ==================================================
# ADMIN: LIST ALL ASSIGNMENTS
# ==================================================

def list_all_assignments():

    with read_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                a.*,
                u.username
            FROM assignments a
            JOIN users u ON u.id = a.user_id
            ORDER BY a.submitted_at DESC
            """
        )

        rows = cur.fetchall()

        return [dict(r) for r in rows]


# ==================================================
# ADMIN: REVIEW ASSIGNMENT
# ==================================================

def review_assignment(assignment_id: int, grade: int, feedback: str):

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
                graded_at=?
            WHERE id=?
            """,
            (grade, feedback, now, assignment_id),
        )


# ==================================================
# GET WEEK GRADE
# ==================================================

def get_week_grade(user_id: int, week: int):

    with read_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT grade
            FROM assignments
            WHERE user_id=?
              AND week=?
              AND status='graded'
            LIMIT 1
            """,
            (user_id, week),
        )

        row = cur.fetchone()

        if not row:
            return None, None

        grade = int(row[0])
        badge = _grade_to_badge(grade)

        return grade, badge


# ==================================================
# GRADE SUMMARY
# ==================================================

def get_student_grade_summary(user_id: int):

    with read_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                week,
                status,
                grade
            FROM assignments
            WHERE user_id=?
            ORDER BY week
            """,
            (user_id,),
        )

        rows = cur.fetchall()

        results = []

        for r in rows:

            grade = r["grade"]

            badge = None
            if grade is not None:
                badge = _grade_to_badge(int(grade))

            results.append(
                {
                    "week": r["week"],
                    "status": r["status"],
                    "grade": grade,
                    "badge": badge,
                }
            )

        return results


# ==================================================
# CERTIFICATE ELIGIBILITY
# ==================================================

def can_issue_certificate(user_id: int) -> bool:

    with read_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COUNT(*)
            FROM assignments
            WHERE user_id=?
              AND status='graded'
            """,
            (user_id,),
        )

        graded = cur.fetchone()[0]

        # Must complete all 6 weeks
        return graded >= 6


# ==================================================
# INTERNAL: GRADE → BADGE
# ==================================================

def _grade_to_badge(score: int) -> str:

    if score >= 80:
        return "Distinction"
    elif score >= 65:
        return "Merit"
    elif score >= 50:
        return "Pass"
    else:
        return "Fail"

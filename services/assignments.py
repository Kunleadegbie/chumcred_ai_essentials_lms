
# services/assignments.py
# ==================================================
# services/assignments.py
# ==================================================

import os
import uuid
import shutil
from datetime import datetime

from services.db import read_conn, write_txn


# ==================================================
# CONFIG
# ==================================================

UPLOAD_ROOT = os.getenv("LMS_UPLOAD_PATH", "/app/data/uploads")
ASSIGNMENT_DIR = os.path.join(UPLOAD_ROOT, "assignments")


# ==================================================
# HELPERS
# ==================================================

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


# ==================================================
# SAVE ASSIGNMENT
# ==================================================

def save_assignment(user_id: int, week: int, uploaded_file):

    # Ensure root folders
    _ensure_dir(ASSIGNMENT_DIR)

    user_dir = os.path.join(ASSIGNMENT_DIR, str(user_id))
    _ensure_dir(user_dir)

    # Build safe filename
    ext = os.path.splitext(uploaded_file.name)[1]
    filename = f"week_{week}_{uuid.uuid4().hex}{ext}"

    # Relative path (PORTABLE)
    relative_path = os.path.join(
        "assignments",
        str(user_id),
        filename
    )

    # Absolute path
    full_path = os.path.join(UPLOAD_ROOT, relative_path)

    # Save file
    with open(full_path, "wb") as f:
        shutil.copyfileobj(uploaded_file, f)

    now = datetime.utcnow().isoformat()

    # Save to DB
    with write_txn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT OR REPLACE INTO assignments
            (user_id, week, file_path, submitted_at, original_filename, status)
            VALUES (?, ?, ?, ?, ?, 'submitted')
            """,
            (
                user_id,
                week,
                relative_path,
                now,
                uploaded_file.name,
            ),
        )


# ==================================================
# CHECK IF SUBMITTED
# ==================================================

def has_assignment(user_id: int, week: int) -> bool:

    with read_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 1 FROM assignments
            WHERE user_id=? AND week=?
            """,
            (user_id, week),
        )

        return cur.fetchone() is not None


# ==================================================
# LIST ALL (ADMIN)
# ==================================================

def list_all_assignments():

    upload_root = os.getenv("LMS_UPLOAD_PATH", "/app/data/uploads")

    with read_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                a.*,
                u.username
            FROM assignments a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.submitted_at DESC
            """
        )

        rows = cur.fetchall()

    results = []

    for r in rows:
        item = dict(r)

        # Rebuild full file path
        item["file_path"] = os.path.join(
            upload_root,
            item["file_path"]
        )

        results.append(item)

    return results


# ==================================================
# REVIEW / GRADE
# ==================================================

def review_assignment(assignment_id, grade, feedback):

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


# ==================================================
# WEEK GRADE
# ==================================================

def get_week_grade(user_id: int, week: int):

    with read_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT grade
            FROM assignments
            WHERE user_id=? AND week=? AND status='graded'
            """,
            (user_id, week),
        )

        row = cur.fetchone()

    if not row:
        return None, None

    grade = row["grade"]

    if grade >= 70:
        badge = "Distinction"
    elif grade >= 50:
        badge = "Merit"
    elif grade >= 40:
        badge = "Pass"
    else:
        badge = "Fail"

    return grade, badge


# ==================================================
# DASHBOARD SUMMARY
# ==================================================

def get_student_grade_summary(user_id: int):

    with read_conn() as conn:
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

    summary = []

    for r in rows:
        item = dict(r)

        if item["status"] == "graded":
            g = item["grade"]

            if g >= 70:
                badge = "Distinction"
            elif g >= 50:
                badge = "Merit"
            elif g >= 40:
                badge = "Pass"
            else:
                badge = "Fail"

            item["badge"] = badge
        else:
            item["badge"] = None

        summary.append(item)

    return summary


# ==================================================
# CERTIFICATE CHECK
# ==================================================

def can_issue_certificate(user_id: int) -> bool:

    with read_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM assignments
            WHERE user_id=? AND status='graded'
            """,
            (user_id,),
        )

        graded = cur.fetchone()["cnt"]

    return graded >= 6

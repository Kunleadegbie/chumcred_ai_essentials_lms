
# services/assignments.py
# services/assignments.py
from datetime import datetime
from services.db import read_conn, write_txn


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def grade_to_badge(score: int | None) -> str | None:
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
def get_assignment_for_week(user_id: int, week: int):
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT week, status, grade, feedback
            FROM assignments
            WHERE user_id = ? AND week = ?
            """,
            (user_id, week),
        )
        return cur.fetchone()


def get_week_grade(user_id: int, week: int):
    row = get_assignment_for_week(user_id, week)
    if not row or row["grade"] is None:
        return None, None
    badge = grade_to_badge(row["grade"])
    return row["grade"], badge


# -------------------------------------------------
# Submission
# -------------------------------------------------
def save_assignment(user_id: int, week: int, uploaded_file):
    file_path = f"uploads/{user_id}_week{week}.pdf"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO assignments (user_id, week, file_path, submitted_at, status)
            VALUES (?, ?, ?, ?, 'submitted')
            ON CONFLICT(user_id, week) DO UPDATE SET
                file_path=excluded.file_path,
                submitted_at=excluded.submitted_at,
                status='submitted'
            """,
            (user_id, week, file_path, datetime.utcnow().isoformat()),
        )


def has_assignment(user_id: int, week: int) -> bool:
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM assignments WHERE user_id=? AND week=?",
            (user_id, week),
        )
        return cur.fetchone() is not None

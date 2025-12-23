# services/progress.py
from __future__ import annotations

from typing import Dict, List, Tuple
from services.db import get_conn

TOTAL_WEEKS = 6


def seed_progress_for_user(user_id: int) -> None:
    """
    Ensure user has progress rows for weeks 1..6.
    RULE: Week 1 unlocked by default; Week 2..6 locked by default.
    This should be called when a student is created.
    """
    conn = get_conn()
    cur = conn.cursor()

    for week in range(1, TOTAL_WEEKS + 1):
        default_status = "unlocked" if week == 1 else "locked"
        # Insert if missing
        cur.execute(
            """
            INSERT OR IGNORE INTO progress (user_id, week, status)
            VALUES (?, ?, ?)
            """,
            (user_id, week, default_status),
        )

    conn.commit()
    conn.close()


def get_progress(user_id: int) -> Dict[int, str]:
    """
    Return {week: status}. Missing weeks treated as locked.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT week, status
        FROM progress
        WHERE user_id = ?
        ORDER BY week
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()

    progress = {week: status for (week, status) in rows}
    # Fill any missing weeks
    for w in range(1, TOTAL_WEEKS + 1):
        progress.setdefault(w, "locked")
    return progress


def mark_week_completed(user_id: int, week: int) -> None:
    """
    Marks ONLY the selected week as completed.
    DOES NOT unlock the next week (admin controls unlocking).
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE progress
        SET status = 'completed'
        WHERE user_id = ? AND week = ?
        """,
        (user_id, week),
    )

    conn.commit()
    conn.close()


def _get_user_id_by_username(username: str) -> int | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_week_status_for_user(username: str, week: int, status: str) -> bool:
    """
    Admin control: set week to 'locked' or 'unlocked' (or even 'completed' if needed).
    Returns True if updated; False if user not found.
    """
    if status not in {"locked", "unlocked", "completed"}:
        raise ValueError("Invalid status")

    user_id = _get_user_id_by_username(username)
    if not user_id:
        return False

    conn = get_conn()
    cur = conn.cursor()

    # Ensure row exists
    cur.execute(
        """
        INSERT OR IGNORE INTO progress (user_id, week, status)
        VALUES (?, ?, 'locked')
        """,
        (user_id, week),
    )

    cur.execute(
        """
        UPDATE progress
        SET status = ?
        WHERE user_id = ? AND week = ?
        """,
        (status, user_id, week),
    )

    conn.commit()
    conn.close()
    return True


def unlock_week_for_user(username: str, week: int) -> bool:
    return set_week_status_for_user(username, week, "unlocked")


def lock_week_for_user(username: str, week: int) -> bool:
    return set_week_status_for_user(username, week, "locked")


def get_user_progress_rows(username: str) -> List[Tuple[int, str]]:
    """
    Admin helper: returns [(week, status), ...]
    """
    user_id = _get_user_id_by_username(username)
    if not user_id:
        return []

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT week, status
        FROM progress
        WHERE user_id = ?
        ORDER BY week
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [(w, s) for (w, s) in rows]


def set_week_status_for_cohort(cohort: str, week: int, status: str) -> int:
    """
    Bulk lock/unlock for a cohort.
    Does NOT overwrite completed weeks.
    Returns number of rows updated.
    """
    if status not in {"locked", "unlocked"}:
        raise ValueError("status must be 'locked' or 'unlocked'")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE progress
        SET status = ?
        WHERE user_id IN (
            SELECT id FROM users
            WHERE role='student' AND COALESCE(cohort, 'Cohort 1') = ?
        )
        AND week = ?
        AND status != 'completed'
    """, (status, cohort, week))

    count = cur.rowcount
    conn.commit()
    conn.close()
    return count


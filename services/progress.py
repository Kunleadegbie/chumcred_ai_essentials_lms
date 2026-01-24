

# --------------------------------------------------
# services/progress.py
# --------------------------------------------------

# ==========================================================
# services/progress.py — CLEAN, STABLE, WEEK-0 SAFE
# ==========================================================

from __future__ import annotations

from datetime import datetime
from typing import Dict

from services.db import read_conn, write_txn

TOTAL_WEEKS = 6          # Weeks 1–6
ORIENTATION_WEEK = 0     # Week 0


# ==========================================================
# INITIAL SEEDING
# ==========================================================
def seed_progress_for_user(user_id: int) -> None:
    """
    Creates progress rows for Week 0..6 for a new student.

    Policy:
    - Week 0: unlocked by default
    - Week 1..6: locked by default
    - Week 1 unlocks ONLY after Week 0 completion
    - Week 2..6 unlock ONLY by admin
    """
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        # Week 0 (Orientation)
        cur.execute(
            """
            INSERT OR IGNORE INTO progress (user_id, week, status, override_by_admin, updated_at)
            VALUES (?, 0, 'unlocked', 0, ?)
            """,
            (user_id, now),
        )

        # Weeks 1–6 (locked)
        for week in range(1, TOTAL_WEEKS + 1):
            cur.execute(
                """
                INSERT OR IGNORE INTO progress (user_id, week, status, override_by_admin, updated_at)
                VALUES (?, ?, 'locked', 0, ?)
                """,
                (user_id, week, now),
            )


# ==========================================================
# READ PROGRESS
# ==========================================================
def get_progress(user_id: int) -> Dict[int, str]:
    """
    Returns progress as {week: status} for Week 0..6.
    """
    with read_conn() as conn:
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

    progress: Dict[int, str] = {}

    for row in rows:
        progress[int(row["week"])] = str(row["status"])

    # Defensive defaults
    progress.setdefault(ORIENTATION_WEEK, "unlocked")
    for week in range(1, TOTAL_WEEKS + 1):
        progress.setdefault(week, "locked")

    return progress


def is_week_unlocked(user_id: int, week: int) -> bool:
    """
    Returns True if a week is unlocked or completed.
    """
    status = get_progress(user_id).get(week, "locked")
    return status in ("unlocked", "completed")


# ==========================================================
# WEEK 0 (ORIENTATION)
# ==========================================================
def is_orientation_completed(user_id: int) -> bool:
    """
    Returns True if Week 0 is completed.
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT status
            FROM progress
            WHERE user_id = ? AND week = 0
            """,
            (user_id,),
        )
        row = cur.fetchone()

    return row is not None and row["status"] == "completed"


def mark_orientation_completed(user_id: int) -> None:
    """
    Marks Week 0 completed and unlocks Week 1.
    """
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        # Mark Week 0 completed
        cur.execute(
            """
            UPDATE progress
            SET status = 'completed', updated_at = ?
            WHERE user_id = ? AND week = 0
            """,
            (now, user_id),
        )

        # Unlock Week 1 (ONLY if not admin-locked)
        cur.execute(
            """
            UPDATE progress
            SET status = 'unlocked', updated_at = ?
            WHERE user_id = ?
              AND week = 1
              AND override_by_admin = 0
            """,
            (now, user_id),
        )


# ==========================================================
# WEEK COMPLETION
# ==========================================================
def mark_week_completed(user_id: int, week: int) -> None:
    """
    Marks a week completed.

    IMPORTANT:
    - Completing Week 0 unlocks Week 1
    - Completing Week 1+ does NOT unlock next week
    """
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE progress
            SET status = 'completed', updated_at = ?
            WHERE user_id = ? AND week = ?
            """,
            (now, user_id, week),
        )

        # Only Week 0 auto-unlocks Week 1
        if week == ORIENTATION_WEEK:
            cur.execute(
                """
                UPDATE progress
                SET status = 'unlocked', updated_at = ?
                WHERE user_id = ? AND week = 1 AND status = 'locked'
                """,
                (now, user_id),
            )


# ==========================================================
# ADMIN CONTROLS
# ==========================================================
def admin_unlock_week(user_id: int, week: int) -> None:
    """
    Admin unlocks a week explicitly.
    """
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE progress
            SET status = 'unlocked', override_by_admin = 1, updated_at = ?
            WHERE user_id = ? AND week = ?
            """,
            (now, user_id, week),
        )


def admin_lock_week(user_id: int, week: int) -> None:
    """
    Admin locks a week explicitly.
    Week 0 is NEVER locked.
    """
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        if week == ORIENTATION_WEEK:
            cur.execute(
                """
                UPDATE progress
                SET status = 'unlocked', override_by_admin = 1, updated_at = ?
                WHERE user_id = ? AND week = 0
                """,
                (now, user_id),
            )
            return

        cur.execute(
            """
            UPDATE progress
            SET status = 'locked', override_by_admin = 1, updated_at = ?
            WHERE user_id = ? AND week = ?
            """,
            (now, user_id, week),
        )


# ==========================================================
# BACKWARD-COMPATIBILITY (DO NOT REMOVE)
# ==========================================================
def unlock_week_for_user(user_id: int, week: int):
    return admin_unlock_week(user_id, week)


def lock_week_for_user(user_id: int, week: int):
    return admin_lock_week(user_id, week)

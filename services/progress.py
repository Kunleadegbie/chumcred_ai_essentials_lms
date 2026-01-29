

# --------------------------------------------------
# services/progress.py
# --------------------------------------------------

# ==========================================================
# services/progress.py — CLEAN, STABLE, WEEK-0 SAFE
# ==========================================================

from __future__ import annotations

from datetime import datetime
from typing import Dict

from services.db import read_conn
from services.db import write_txn

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
def mark_orientation_completed(user_id):
    from datetime import datetime
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        # Check if record exists
        cur.execute(
            "SELECT id FROM progress WHERE user_id=? AND week=0",
            (user_id,)
        )
        row = cur.fetchone()

        if row:
            # Update
            cur.execute("""
                UPDATE progress
                SET orientation_done=1,
                    status='completed',
                    updated_at=?
                WHERE user_id=? AND week=0
            """, (now, user_id))

        else:
            # Insert
            cur.execute("""
                INSERT INTO progress
                (user_id, week, status, orientation_done, updated_at)
                VALUES (?, 0, 'completed', 1, ?)
            """, (user_id, now))


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




# ==========================================================
# WEEK COMPLETION
# ==========================================================
def mark_week_completed(user_id, week):

    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        # Check if record exists
        cur.execute("""
            SELECT id FROM progress
            WHERE user_id=? AND week=?
        """, (user_id, week))

        row = cur.fetchone()

        if row:
            # Update existing
            cur.execute("""
                UPDATE progress
                SET status='completed',
                    updated_at=?
                WHERE user_id=? AND week=?
            """, (now, user_id, week))

        else:
            # Insert new
            cur.execute("""
                INSERT INTO progress
                (user_id, week, status, updated_at)
                VALUES (?, ?, 'completed', ?)
            """, (user_id, week, now))

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


def sync_user_progress(user_id: int, total_weeks: int = 6):
    """
    Ensure a user has progress rows for Week 0 - Week N.
    Safe: does not overwrite existing records.
    """

    from services.db import write_txn
    from datetime import datetime

    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        # Get existing weeks
        cur.execute(
            "SELECT week FROM progress WHERE user_id=?",
            (user_id,),
        )

        existing = {row["week"] for row in cur.fetchall()}

        # Week 0 (Orientation)
        if 0 not in existing:
            cur.execute(
                """
                INSERT INTO progress (user_id, week, status)
                VALUES (?, 0, 'unlocked')
                """,
                (user_id,),
            )

        # Weeks 1..N
        for week in range(1, total_weeks + 1):

            if week not in existing:

                status = "locked"
                if week == 1:
                    status = "unlocked"

                cur.execute(
                    """
                    INSERT INTO progress (user_id, week, status)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, week, status),
                )

def mark_week_completed(user_id, week):
    from datetime import datetime
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        # Check if record exists
        cur.execute(
            "SELECT id FROM progress WHERE user_id=? AND week=?",
            (user_id, week)
        )
        row = cur.fetchone()

        if row:
            # Update
            cur.execute("""
                UPDATE progress
                SET status='completed',
                    updated_at=?
                WHERE user_id=? AND week=?
            """, (now, user_id, week))

        else:
            # Insert
            cur.execute("""
                INSERT INTO progress
                (user_id, week, status, orientation_done, updated_at)
                VALUES (?, ?, 'completed', 0, ?)
            """, (user_id, week, now))


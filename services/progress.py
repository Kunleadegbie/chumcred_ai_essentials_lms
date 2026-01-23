

# --------------------------------------------------
# services/progress.py
# --------------------------------------------------

# services/progress.py

from datetime import datetime
from services.db import write_txn, read_conn

TOTAL_WEEKS = 6

def unlock_week_for_user(user_id: int, week: int):
    """
    Backward-compatible alias for admin week unlock.
    Keeps existing admin.py imports working without changes.
    """
    return admin_unlock_week(user_id, week)

def seed_progress_for_user(user_id: int):
    """
    Week 0: unlocked by default
    Weeks 1–6: locked by default
    """
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        # Week 0 (Orientation)
        cur.execute(
            """
            INSERT OR IGNORE INTO progress (user_id, week, status, updated_at)
            VALUES (?, 0, 'unlocked', ?)
            """,
            (user_id, now),
        )

        # Weeks 1–6
        for week in range(1, TOTAL_WEEKS + 1):
            cur.execute(
                """
                INSERT OR IGNORE INTO progress (user_id, week, status, updated_at)
                VALUES (?, ?, 'locked', ?)
                """,
                (user_id, week, now),
            )


def get_progress(user_id: int) -> dict:
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT week, status FROM progress WHERE user_id=?",
            (user_id,),
        )
        return {row["week"]: row["status"] for row in cur.fetchall()}


def mark_week_completed(user_id: int, week: int):
    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE progress
            SET status='completed', updated_at=?
            WHERE user_id=? AND week=?
            """,
            (datetime.utcnow().isoformat(), user_id, week),
        )


def admin_unlock_week(user_id: int, week: int):
    """
    Admin explicitly unlocks Week 1–6
    """
    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE progress
            SET status='unlocked', override_by_admin=1, updated_at=?
            WHERE user_id=? AND week=?
            """,
            (datetime.utcnow().isoformat(), user_id, week),
        )

# ==========================================================
# BACKWARD-COMPATIBILITY ALIASES (DO NOT REMOVE)
# Keeps existing admin.py imports working
# ==========================================================

def unlock_week_for_user(user_id: int, week: int):
    """
    Alias for admin unlock.
    """
    return admin_unlock_week(user_id, week)


def lock_week_for_user(user_id: int, week: int):
    """
    Alias for admin lock.
    """
    return admin_lock_week(user_id, week)


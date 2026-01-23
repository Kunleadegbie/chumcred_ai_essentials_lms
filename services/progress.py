

# --------------------------------------------------
# services/progress.py
# --------------------------------------------------

from datetime import datetime
from services.db import write_txn, read_conn

TOTAL_WEEKS = 6  # Weeks 1–6 (Week 0 = Orientation)


# --------------------------------------------------
# Seed progress for a new student
# --------------------------------------------------
def seed_progress_for_user(user_id: int) -> None:
    """
    Week 0: unlocked (mandatory orientation)
    Week 1–6: locked by default (admin-controlled)
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

        # Weeks 1–6
        for week in range(1, TOTAL_WEEKS + 1):
            cur.execute(
                """
                INSERT OR IGNORE INTO progress (user_id, week, status, override_by_admin, updated_at)
                VALUES (?, ?, 'locked', 0, ?)
                """,
                (user_id, week, now),
            )


# --------------------------------------------------
# Get progress map {week: status}
# --------------------------------------------------
def get_progress(user_id: int) -> dict[int, str]:
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT week, status FROM progress WHERE user_id=?",
            (user_id,),
        )
        rows = cur.fetchall()

    return {row["week"]: row["status"] for row in rows}


# --------------------------------------------------
# Mark a week as completed
# --------------------------------------------------
def mark_week_completed(user_id: int, week: int) -> None:
    """
    Marks ONLY the given week as completed.
    Does NOT auto-unlock next week (admin decides).
    """
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE progress
            SET status='completed', updated_at=?
            WHERE user_id=? AND week=?
            """,
            (now, user_id, week),
        )


# --------------------------------------------------
# Admin unlock / lock controls
# --------------------------------------------------
def unlock_week_for_user(user_id: int, week: int) -> None:
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE progress
            SET status='unlocked', override_by_admin=1, updated_at=?
            WHERE user_id=? AND week=?
            """,
            (now, user_id, week),
        )


def lock_week_for_user(user_id: int, week: int) -> None:
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE progress
            SET status='locked', override_by_admin=1, updated_at=?
            WHERE user_id=? AND week=?
            """,
            (now, user_id, week),
        )

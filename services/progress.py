

# --------------------------------------------------
# services/progress.py
# --------------------------------------------------

# services/progress.py
from __future__ import annotations

from datetime import datetime
from typing import Dict

from services.db import read_conn, write_txn

TOTAL_WEEKS = 6  # Week 1–6
ORIENTATION_WEEK = 0


def seed_progress_for_user(user_id: int) -> None:
    """
    Creates progress rows for Week 0..6 for a new student.
    Policy:
      - Week 0: unlocked by default
      - Week 1..6: locked by default (Week 1 becomes unlocked only after Week 0 completion)
      - Week 2..6 remain locked until Admin unlocks them (no auto-unlock)
    """
    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        # Week 0
        cur.execute(
            """
            INSERT OR IGNORE INTO progress (user_id, week, status, override_by_admin, updated_at)
            VALUES (?, ?, 'unlocked', 0, ?)
            """,
            (user_id, ORIENTATION_WEEK, now),
        )

        # Weeks 1..6
        for w in range(1, TOTAL_WEEKS + 1):
            cur.execute(
                """
                INSERT OR IGNORE INTO progress (user_id, week, status, override_by_admin, updated_at)
                VALUES (?, ?, 'locked', 0, ?)
                """,
                (user_id, w, now),
            )


def get_progress(user_id: int) -> Dict[int, str]:
    """
    Returns {week:int -> status:str} for Week 0..6.
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

    prog: Dict[int, str] = {}
    for r in rows:
        week = int(r["week"])
        status = str(r["status"])
        prog[week] = status

    # Defensive defaults (in case DB missing rows)
    if ORIENTATION_WEEK not in prog:
        prog[ORIENTATION_WEEK] = "unlocked"
    for w in range(1, TOTAL_WEEKS + 1):
        prog.setdefault(w, "locked")

    return prog


def is_week_unlocked(user_id: int, week: int) -> bool:
    prog = get_progress(user_id)
    return prog.get(week, "locked") in ("unlocked", "completed")

from datetime import datetime
from services.db import write_txn


def mark_orientation_completed(user_id: int):
    """
    Marks Week 0 as completed and unlocks Week 1.
    This is REQUIRED before Week 1 becomes accessible.
    """

    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        # 1️⃣ Mark Week 0 completed
        cur.execute(
            """
            UPDATE progress
            SET status = 'completed', updated_at = ?
            WHERE user_id = ? AND week = 0
            """,
            (now, user_id),
        )

        # 2️⃣ Unlock Week 1 (ONLY if not admin-locked)
        cur.execute(
            """
            UPDATE progress
            SET status = 'unlocked', updated_at = ?
            WHERE user_id = ? AND week = 1
              AND override_by_admin = 0
            """,
            (now, user_id),
        )



def admin_unlock_week(user_id: int, week: int) -> None:
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


def admin_lock_week(user_id: int, week: int) -> None:
    """
    Admin can lock any week (except Week 0 stays unlocked for onboarding).
    If admin locks week=0, we still force it unlocked.
    """
    now = datetime.utcnow().isoformat()
    with write_txn() as conn:
        cur = conn.cursor()

        if week == ORIENTATION_WEEK:
            cur.execute(
                """
                UPDATE progress
                SET status='unlocked', override_by_admin=1, updated_at=?
                WHERE user_id=? AND week=?
                """,
                (now, user_id, ORIENTATION_WEEK),
            )
            return

        cur.execute(
            """
            UPDATE progress
            SET status='locked', override_by_admin=1, updated_at=?
            WHERE user_id=? AND week=?
            """,
            (now, user_id, week),
        )


def mark_week_completed(user_id: int, week: int) -> None:
    """
    Marks a week completed.
    IMPORTANT POLICY:
      - Completing Week 0 unlocks Week 1 automatically.
      - Completing Week 1 does NOT unlock Week 2 (Admin must unlock).
      - Weeks 2..6 do NOT auto-unlock next week.
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

        # Only Week 0 completion unlocks Week 1
        if week == ORIENTATION_WEEK:
            cur.execute(
                """
                UPDATE progress
                SET status='unlocked', updated_at=?
                WHERE user_id=? AND week=1 AND status='locked'
                """,
                (now, user_id),
            )


# ==========================================================
# BACKWARD-COMPATIBILITY ALIASES (DO NOT REMOVE)
# Keeps existing admin.py imports working
# ==========================================================

def unlock_week_for_user(user_id: int, week: int):
    return admin_unlock_week(user_id, week)


def lock_week_for_user(user_id: int, week: int):
    return admin_lock_week(user_id, week)


# -------------------------------------------------
# WEEK 0 (ORIENTATION) HELPERS
# -------------------------------------------------

def is_orientation_completed(user_id: int) -> bool:
    """
    Returns True if Week 0 is completed.
    Week 0 is stored as week = 0 in progress table.
    """
    from services.db import read_conn

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
    Marks Week 0 as completed and unlocks Week 1.
    """
    from services.db import write_txn
    from datetime import datetime

    now = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        # Mark Week 0 completed
        cur.execute(
            """
            INSERT INTO progress (user_id, week, status, updated_at)
            VALUES (?, 0, 'completed', ?)
            ON CONFLICT(user_id, week) DO UPDATE SET
                status = 'completed',
                updated_at = excluded.updated_at
            """,
            (user_id, now),
        )

        # Unlock Week 1 (but NOT auto-complete it)
        cur.execute(
            """
            INSERT INTO progress (user_id, week, status, updated_at)
            VALUES (?, 1, 'unlocked', ?)
            ON CONFLICT(user_id, week) DO UPDATE SET
                status = 'unlocked',
                updated_at = excluded.updated_at
            """,
            (user_id, now),
        )


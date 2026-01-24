

# services/help.py
from services.db import read_conn


def list_active_broadcasts(limit: int = 1):
    """
    Returns the most recent active broadcast messages.
    Used on student dashboard popup.
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, subject, message, created_at
            FROM broadcasts
            WHERE status = 'active'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def list_all_broadcasts():
    """
    Used by admin to view/manage broadcasts.
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM broadcasts
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


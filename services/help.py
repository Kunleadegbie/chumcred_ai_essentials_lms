

# services/help.py

# services/help.py
from services.db import read_conn


def list_active_broadcasts(limit: int = 5):
    """
    Returns latest active broadcasts as a list of DICTs
    so UI can safely use .get("subject"), etc.
    """
    with read_conn() as conn:
        cur = conn.cursor()

        limit = int(limit)  # safety

        # Use parameterized LIMIT (safer than f-string)
        cur.execute(
            """
            SELECT id, subject, message, created_at
            FROM broadcasts
            WHERE active = 1
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cur.fetchall()

        # Convert sqlite3.Row -> dict (so .get works in UI)
        return [dict(r) for r in rows]


def list_all_broadcasts():
    """
    Used by admin to view/manage broadcasts.
    Returns list of dicts.
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

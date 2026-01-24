

# services/help.py
from services.db import read_conn


def list_active_broadcasts(limit: int = 5):
    with read_conn() as conn:
        cur = conn.cursor()

        limit = int(limit)  # safety

        cur.execute(f"""
            SELECT id, message, created_at
            FROM broadcasts
            WHERE active = 1
            ORDER BY created_at DESC
            LIMIT {limit}
        """)

        return cur.fetchall()


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


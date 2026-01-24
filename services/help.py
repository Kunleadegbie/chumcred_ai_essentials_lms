

# services/help.py

# services/help.py
from services.db import read_conn


def list_active_broadcasts(limit: int = 5):
    """
    Returns latest active broadcasts as LIST[DICT]
    """
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, subject, message, created_at
            FROM broadcasts
            WHERE active = 1
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def list_student_tickets(user_id: int):
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, subject, message, admin_reply, status, created_at
            FROM support_tickets
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]

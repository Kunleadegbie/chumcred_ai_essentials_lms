from datetime import datetime
from services.db import read_conn, write_txn


def create_broadcast(title, message, admin_id):
    with write_txn() as conn:
        conn.execute(
            """
            INSERT INTO broadcasts (title, message, created_by, created_at, active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (title, message, admin_id, datetime.utcnow().isoformat()),
        )


def get_active_broadcasts():
    with read_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM broadcasts
            WHERE active = 1
            ORDER BY created_at DESC
            """
        ).fetchall()


def has_read(broadcast_id, user_id):
    with read_conn() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM broadcast_reads
            WHERE broadcast_id = ? AND user_id = ?
            """,
            (broadcast_id, user_id),
        ).fetchone()
        return row is not None


def mark_as_read(broadcast_id, user_id):
    with write_txn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO broadcast_reads
            (broadcast_id, user_id, read_at)
            VALUES (?, ?, ?)
            """,
            (broadcast_id, user_id, datetime.utcnow().isoformat()),
        )

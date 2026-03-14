from services.db import write_txn
from datetime import datetime

print("📌 Cleaning duplicate broadcasts...")

with write_txn() as conn:
    cur = conn.cursor()

    # Find duplicates by message + same day
    cur.execute("""
        SELECT message, DATE(created_at) as d, COUNT(*) as cnt
        FROM broadcasts
        GROUP BY message, d
        HAVING cnt > 1
    """)

    duplicates = cur.fetchall()

    for row in duplicates:
        message = row["message"]
        day = row["d"]

        # Keep the earliest, delete the rest
        cur.execute("""
            DELETE FROM broadcasts
            WHERE id NOT IN (
                SELECT id FROM broadcasts
                WHERE message = ?
                AND DATE(created_at) = ?
                ORDER BY created_at ASC
                LIMIT 1
            )
            AND message = ?
            AND DATE(created_at) = ?
        """, (message, day, message, day))

    conn.commit()

print("✅ Duplicate broadcasts cleaned successfully.")

from services.db import write_txn

with write_txn() as conn:
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_reads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            broadcast_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            read_at TEXT NOT NULL,
            UNIQUE(broadcast_id, user_id)
        )
    """)

    conn.commit()

print("✅ broadcast_reads table ready.")

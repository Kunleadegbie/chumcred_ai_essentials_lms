from services.db import write_txn

with write_txn() as conn:
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            message TEXT,
            created_at TEXT
        )
    """)

    conn.commit()

print("✅ Support table ready.")

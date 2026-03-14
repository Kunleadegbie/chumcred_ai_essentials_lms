from services.db import write_txn

with write_txn() as conn:
    cur = conn.cursor()
    cur.execute("""
        UPDATE support_messages
        SET status = 'open'
        WHERE status IS NULL
    """)
    conn.commit()

print("✅ All support messages set to open.")

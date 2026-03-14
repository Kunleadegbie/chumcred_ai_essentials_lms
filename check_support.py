from services.db import write_txn

with write_txn() as conn:
    cur = conn.cursor()
    try:
        cur.execute("""
            ALTER TABLE support_messages
            ADD COLUMN status TEXT DEFAULT 'open'
        """)
        conn.commit()
        print("✅ status column added successfully.")
    except Exception as e:
        print("ℹ️ status column already exists or skipped:", e)

print("Done.")

from services.db import write_txn

with write_txn() as conn:
    cur = conn.cursor()

    try:
        cur.execute("""
        ALTER TABLE progress
        ADD COLUMN updated_at TEXT
        """)
        print("✅ Column updated_at added.")
    except Exception as e:
        print("ℹ️ Column already exists or skipped:", e)


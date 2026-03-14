from services.db import write_txn

print("🔧 Fixing support_messages table...")

with write_txn() as conn:
    cur = conn.cursor()

    try:
        cur.execute("""
            ALTER TABLE support_messages
            ADD COLUMN status TEXT DEFAULT 'open'
        """)
        print("✅ 'status' column added.")
    except Exception as e:
        print("ℹ️ Status column already exists or skipped:", e)

print("🎉 Done.")

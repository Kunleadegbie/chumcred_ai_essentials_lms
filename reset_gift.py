from services.db import write_txn
import bcrypt

USERNAME = "Gift Nwokoye"   # change if username is different
NEW_PASSWORD = "GiftN@26"

hashed = bcrypt.hashpw(NEW_PASSWORD.encode(), bcrypt.gensalt())

with write_txn() as conn:
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET password_hash = ?, active = 1
        WHERE username = ?
    """, (hashed, USERNAME))

    if cur.rowcount == 0:
        print("❌ User not found:", USERNAME)
    else:
        print("✅ Password reset successful for:", USERNAME)

print("Done.")

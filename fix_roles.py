# fix_roles.py

from services.db import write_txn

print("📌 Fixing missing user roles...")

with write_txn() as conn:
    cur = conn.cursor()

    # Set role = student where missing
    cur.execute("""
        UPDATE users
        SET role = 'student'
        WHERE role IS NULL OR role = ''
    """)

    conn.commit()

print("✅ All missing roles fixed successfully.")

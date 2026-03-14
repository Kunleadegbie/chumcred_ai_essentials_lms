from services.db import write_txn
import bcrypt

# 🔧 EDIT THIS LIST
STUDENTS = [
    {"username": "Gift Nwokoye", "password": "lmsaicohort101"},
    {"username": "Taiwo Adegbola", "password": "lmsaicohort102"},
    {"username": "Adediwura Sowande", "password": "lmsaicohort103"},
    {"username": "Alex Chunedu Chineke", "password": "lmsaicohort104"},
]

with write_txn() as conn:
    cur = conn.cursor()

    for s in STUDENTS:
        pw_hash = bcrypt.hashpw(
            s["password"].encode(),
            bcrypt.gensalt()
        )

        cur.execute("""
            INSERT OR IGNORE INTO users
            (username, password_hash, role, active)
            VALUES (?, ?, 'student', 1)
        """, (s["username"], pw_hash))

        print(f"✅ Migrated: {s['username']}")

    conn.commit()

print("🎉 Rescue completed.")

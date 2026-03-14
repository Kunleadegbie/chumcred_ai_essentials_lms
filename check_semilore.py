from services.db import read_conn

print("🔍 Checking progress for user_id = 6 (Semilore)")

with read_conn() as conn:
    rows = conn.execute("""
        SELECT *
        FROM progress
        WHERE user_id = 6
        ORDER BY week
    """).fetchall()

    data = [dict(r) for r in rows]
    print(data)


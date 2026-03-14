from services.db import read_conn

with read_conn() as conn:
    rows = conn.execute("""
        SELECT user_id, week, grade, feedback
        FROM assignments
    """).fetchall()

print([dict(r) for r in rows])

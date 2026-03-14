from services.db import read_conn

print("🔍 Searching for Semilore...")

with read_conn() as conn:
    rows = conn.execute("""
        SELECT id, username
        FROM users
        WHERE username LIKE '%Semilore%'
           OR username LIKE '%semi%'
    """).fetchall()

    for r in rows:
        print(dict(r))

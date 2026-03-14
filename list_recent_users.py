from services.db import read_conn

with read_conn() as conn:
    rows = conn.execute(
        "SELECT id, username, role FROM users ORDER BY id DESC LIMIT 20"
    ).fetchall()

    for r in rows:
        print(dict(r))

from services.db import read_conn

KEYWORD = "Gift"   # you can change later e.g. "Nwokoye"

with read_conn() as conn:
    rows = conn.execute(
        "SELECT id, username, role FROM users WHERE username LIKE ? ORDER BY id DESC",
        (f"%{KEYWORD}%",)
    ).fetchall()

    print(f"Matches for '{KEYWORD}':", len(rows))
    for r in rows:
        print(dict(r))

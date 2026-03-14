# verify.py
import sqlite3
from config import DB_PATH, UPLOAD_ROOT

print(f"📌 USING DATABASE: {DB_PATH}")
print(f"📌 UPLOAD ROOT: {UPLOAD_ROOT}")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print("📚 TABLES:", [t["name"] for t in tables])

for t in tables:
    name = t["name"]
    cnt = conn.execute(f"SELECT COUNT(*) AS c FROM {name}").fetchone()["c"]
    print(f"🔢 {name}: {cnt} rows")

# Try reading tickets from the canonical table name
try:
    rows = conn.execute("""
        SELECT id, created_at, student_name, status, subject
        FROM help_support_tickets
        ORDER BY datetime(created_at) DESC
        LIMIT 10
    """).fetchall()
    print("🧾 Latest help_support_tickets:", [dict(r) for r in rows])
except Exception as e:
    print("⚠️ Could not read help_support_tickets:", e)

conn.close()

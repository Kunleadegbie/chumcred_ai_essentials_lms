from services.db import get_conn


# ======================================================
# SEED DEFAULT ADMIN (ONE SOURCE OF TRUTH)
# ======================================================

import sqlite3
from services.db import get_conn

def seed_data():
    conn = get_conn()
    cur = conn.cursor()

    # Seed admin user
    cur.execute("""
    INSERT OR IGNORE INTO users (username, password, role)
    VALUES (?, ?, ?)
    """, ("admin", "admin123", "admin"))

    conn.commit()
    conn.close()

# ======================================================
# SEED PROGRAM STRUCTURE (WEEKS & ASSIGNMENTS)
# ======================================================
def seed_program():
    conn = get_conn()
    cur = conn.cursor()

    # ---------------- MODULES ----------------
    cur.execute("SELECT COUNT(*) FROM modules")
    if cur.fetchone()[0] == 0:
        weeks = [
            (1, "Understanding AI & LLMs"),
            (2, "Mastering Prompting"),
            (3, "AI for Productivity, Career & School"),
            (4, "AI for Content Creation & Design"),
            (5, "AI for Websites & No-Code Tools"),
            (6, "AI for Monetization")
        ]
        for w, t in weeks:
            cur.execute(
                "INSERT INTO modules (week, title) VALUES (?, ?)",
                (w, t)
            )

    # ---------------- ASSIGNMENTS ----------------
    cur.execute("SELECT COUNT(*) FROM assignments")
    if cur.fetchone()[0] == 0:
        for w in range(1, 7):
            cur.execute("""
                INSERT INTO assignments (week, title, prompt)
                VALUES (?, ?, ?)
            """, (
                w,
                f"Week {w} Assignment",
                f"Submit Week {w} project"
            ))

    conn.commit()
    conn.close()

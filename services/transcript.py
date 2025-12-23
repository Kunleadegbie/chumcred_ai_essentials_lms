import os
from datetime import datetime
from services.db import get_conn

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSCRIPT_DIR = os.path.join(BASE_DIR, "generated", "transcripts")
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)


def generate_transcript(user_id, username):
    """
    Generates a transcript-style completion report.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT week, completed
    FROM progress
    WHERE user_id=?
    ORDER BY week
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    completed_weeks = [r for r in rows if r[1] == 1]

    filename = f"transcript_user{user_id}.txt"
    file_path = os.path.join(TRANSCRIPT_DIR, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("CHUMCRED ACADEMY\n")
        f.write("AI ESSENTIALS — COMPLETION TRANSCRIPT\n\n")
        f.write(f"Student Name: {username}\n")
        f.write(f"Issue Date: {datetime.utcnow().strftime('%Y-%m-%d')}\n\n")
        f.write("Completed Modules:\n")

        for week, _ in completed_weeks:
            f.write(f"✔ Week {week}\n")

        f.write("\nStatus: PROGRAM COMPLETED\n")

    return file_path

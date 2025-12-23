# services/transcript_generator.py
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from services.db import get_conn


def generate_transcript(user: dict) -> str:
    """
    Generates a simple transcript PDF into generated_transcripts/.
    Returns the file path.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT week, status
        FROM progress
        WHERE user_id = ?
        ORDER BY week
        """,
        (user["id"],),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise ValueError("No progress data found for this student.")

    os.makedirs("generated_transcripts", exist_ok=True)
    path = os.path.join("generated_transcripts", f"transcript_{user['id']}.pdf")

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, y, "CHUMCRED ACADEMY — AI ESSENTIALS")
    y -= 22
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y, "Transcript / Completion Report")

    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(60, y, f"Student: {user.get('username', '')}")
    y -= 16
    c.drawString(60, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 24

    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, y, "Week")
    c.drawString(140, y, "Status")
    y -= 14
    c.setFont("Helvetica", 11)

    for week, status in rows:
        c.drawString(60, y, f"Week {week}")
        c.drawString(140, y, str(status).capitalize())
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 11)

    c.save()
    return path

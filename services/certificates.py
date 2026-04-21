import os
import re
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import Color
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

from services.db import read_conn, write_txn


# ✅ persistent folder (Railway volume should be mounted to /app/data)
OUTPUT_DIR = os.getenv("CERT_OUTPUT_DIR", "/app/data/generated_certificates")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _safe_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^a-zA-Z0-9 _-]+", "", name)
    name = re.sub(r"\s+", "_", name)
    return name or "Student"


def _ensure_cert_table():
    """
    Ensure certificates table exists and has required columns.
    Non-destructive.
    """
    with write_txn() as conn:
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='certificates'"
        ).fetchone()

        if not exists:
            conn.execute(
                """
                CREATE TABLE certificates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    issued_at TEXT,
                    certificate_path TEXT
                )
                """
            )
            conn.commit()
            return

        cols = [r[1] for r in conn.execute("PRAGMA table_info(certificates)").fetchall()]
        if "user_id" not in cols:
            conn.execute("ALTER TABLE certificates ADD COLUMN user_id INTEGER")
        if "issued_at" not in cols:
            conn.execute("ALTER TABLE certificates ADD COLUMN issued_at TEXT")
        if "certificate_path" not in cols:
            conn.execute("ALTER TABLE certificates ADD COLUMN certificate_path TEXT")
        conn.commit()


def has_certificate(user_id: int) -> bool:
    _ensure_cert_table()
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM certificates WHERE user_id=? LIMIT 1", (int(user_id),))
        return cur.fetchone() is not None


def get_certificate_record(user_id: int):
    _ensure_cert_table()
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, user_id, issued_at, certificate_path "
            "FROM certificates WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (int(user_id),),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def _fit_font_size(text: str, font: str, max_size: int, min_size: int, max_width: float) -> int:
    size = max_size
    while size > min_size:
        if stringWidth(text, font, size) <= max_width:
            return size
        size -= 1
    return min_size


def _draw_premium_background(c: canvas.Canvas, w: float, h: float) -> None:
    """
    Create a premium-looking colorful background without external images:
    - soft base fill
    - diagonal color bands
    - subtle circles / accents
    """
    # Base (very light)
    c.setFillColor(Color(0.97, 0.98, 0.99))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Diagonal bands (top-left to bottom-right vibe)
    c.setFillColor(Color(0.12, 0.46, 0.96, alpha=0.10))  # soft blue
    c.saveState()
    c.translate(-w * 0.2, h * 0.15)
    c.rotate(-12)
    c.rect(0, h * 0.55, w * 1.4, h * 0.16, fill=1, stroke=0)
    c.restoreState()

    c.setFillColor(Color(0.95, 0.42, 0.47, alpha=0.10))  # soft coral
    c.saveState()
    c.translate(-w * 0.1, h * 0.05)
    c.rotate(-12)
    c.rect(0, h * 0.32, w * 1.4, h * 0.14, fill=1, stroke=0)
    c.restoreState()

    c.setFillColor(Color(0.22, 0.78, 0.66, alpha=0.10))  # soft teal
    c.saveState()
    c.translate(-w * 0.05, -h * 0.10)
    c.rotate(-12)
    c.rect(0, h * 0.12, w * 1.4, h * 0.12, fill=1, stroke=0)
    c.restoreState()

    # Accent circles (subtle)
    c.setFillColor(Color(0.12, 0.46, 0.96, alpha=0.08))
    c.circle(w * 0.90, h * 0.80, 85, fill=1, stroke=0)

    c.setFillColor(Color(0.95, 0.42, 0.47, alpha=0.08))
    c.circle(w * 0.12, h * 0.25, 75, fill=1, stroke=0)

    c.setFillColor(Color(0.22, 0.78, 0.66, alpha=0.06))
    c.circle(w * 0.82, h * 0.20, 55, fill=1, stroke=0)


def _draw_border(c: canvas.Canvas, w: float, h: float) -> None:
    margin = 14 * mm

    # Outer border
    c.setLineWidth(2.2)
    c.setStrokeColor(Color(0.10, 0.15, 0.22, alpha=0.55))
    c.roundRect(margin, margin, w - 2 * margin, h - 2 * margin, 14, stroke=1, fill=0)

    # Inner border
    c.setLineWidth(1.0)
    c.setStrokeColor(Color(0.12, 0.46, 0.96, alpha=0.35))
    c.roundRect(margin + 6, margin + 6, w - 2 * (margin + 6), h - 2 * (margin + 6), 12, stroke=1, fill=0)


def _build_certificate_pdf_landscape(full_name: str, out_path: str) -> str:
    """
    Premium LANDSCAPE certificate with colorful background.
    """
    _ensure_dir(os.path.dirname(out_path))

    page_w, page_h = landscape(A4)
    c = canvas.Canvas(out_path, pagesize=(page_w, page_h))

    # Background + border
    _draw_premium_background(c, page_w, page_h)
    _draw_border(c, page_w, page_h)

    # Layout anchors
    left = 40 * mm
    right = page_w - 40 * mm
    center_x = page_w / 2

    # Header (Brand)
    c.setFillColor(Color(0.08, 0.11, 0.17))
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(center_x, page_h - 38 * mm, "CHUMCRED ACADEMY")

    # Badge line
    c.setFillColor(Color(0.12, 0.46, 0.96))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(center_x, page_h - 55 * mm, "CERTIFICATE OF COMPLETION")

    # Subtitle
    c.setFillColor(Color(0.20, 0.24, 0.30))
    c.setFont("Helvetica", 14)
    c.drawCentredString(center_x, page_h - 70 * mm, "This is to certify that")

    # Name (auto-fit)
    max_name_width = (right - left)
    name_font = "Helvetica-Bold"
    name_size = _fit_font_size(full_name.strip(), name_font, max_size=44, min_size=22, max_width=max_name_width)

    # Name highlight bar (subtle)
    bar_w = min(max_name_width, 160 * mm)
    bar_h = 16 * mm
    bar_y = page_h - 98 * mm
    c.setFillColor(Color(0.12, 0.46, 0.96, alpha=0.10))
    c.roundRect(center_x - bar_w / 2, bar_y - 8, bar_w, bar_h, 10, fill=1, stroke=0)

    c.setFillColor(Color(0.06, 0.08, 0.12))
    c.setFont(name_font, name_size)
    c.drawCentredString(center_x, page_h - 95 * mm, full_name.strip())

    # Program line
    c.setFillColor(Color(0.20, 0.24, 0.30))
    c.setFont("Helvetica", 14)
    c.drawCentredString(center_x, page_h - 115 * mm, "has successfully completed the 6-week online training program")

    c.setFillColor(Color(0.08, 0.11, 0.17))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(center_x, page_h - 128 * mm, "AI Essentials — From Zero to Confident AI User")

    # Issued date
    issued_text = "Issued: " + datetime.now().strftime("%d %b %Y")
    c.setFillColor(Color(0.20, 0.24, 0.30))
    c.setFont("Helvetica", 12)
    c.drawCentredString(center_x, page_h - 145 * mm, issued_text)

    # Footer signature area
    y_sig = 28 * mm
    c.setStrokeColor(Color(0.10, 0.15, 0.22, alpha=0.35))
    c.setLineWidth(1)
    c.line(left, y_sig + 18, left + 90 * mm, y_sig + 18)
    c.line(right - 90 * mm, y_sig + 18, right, y_sig + 18)

    c.setFillColor(Color(0.08, 0.11, 0.17))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y_sig, "Dr. Adekunle Adegbie")
    c.setFillColor(Color(0.20, 0.24, 0.30))
    c.setFont("Helvetica", 11)
    c.drawString(left, y_sig - 12, "Program Coordinator")

    c.setFillColor(Color(0.08, 0.11, 0.17))
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(right, y_sig, "Chumcred Academy")
    c.setFillColor(Color(0.20, 0.24, 0.30))
    c.setFont("Helvetica", 11)
    c.drawRightString(right, y_sig - 12, "Official Certificate")

    # Subtle watermark (optional but premium)
    c.saveState()
    c.setFillColor(Color(0.08, 0.11, 0.17, alpha=0.05))
    c.translate(center_x, page_h / 2)
    c.rotate(20)
    c.setFont("Helvetica-Bold", 64)
    c.drawCentredString(0, 0, "CHUMCRED")
    c.restoreState()

    c.showPage()
    c.save()

    return os.path.abspath(out_path)


def issue_certificate(user_id: int, full_name: str) -> str:
    """
    Generates a certificate PDF (LANDSCAPE + premium background),
    saves it to OUTPUT_DIR, stores absolute path in DB.
    If record exists but file missing, regenerate + update record.
    """
    _ensure_cert_table()

    user_id = int(user_id)
    _ensure_dir(OUTPUT_DIR)

    safe_name = _safe_filename(full_name)
    filename = f"certificate_{safe_name}_{user_id}.pdf"
    out_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))

    rec = get_certificate_record(user_id)

    # If record exists and file exists, return it
    if rec and rec.get("certificate_path") and os.path.exists(rec["certificate_path"]):
        return rec["certificate_path"]

    # Generate NEW premium landscape certificate
    cert_path = _build_certificate_pdf_landscape(full_name.strip(), out_path)
    issued_at = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()

        if rec:
            cur.execute(
                "UPDATE certificates SET issued_at=?, certificate_path=? WHERE id=?",
                (issued_at, cert_path, int(rec["id"])),
            )
        else:
            cur.execute(
                "INSERT INTO certificates (user_id, issued_at, certificate_path) VALUES (?, ?, ?)",
                (user_id, issued_at, cert_path),
            )

        conn.commit()

    return cert_path
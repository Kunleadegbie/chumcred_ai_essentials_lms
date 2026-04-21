import os
import re
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import Color
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

from services.db import read_conn, write_txn

# Persistent folder (make sure Railway volume is mounted to /app/data)
OUTPUT_DIR = os.getenv("CERT_OUTPUT_DIR", "/app/data/generated_certificates")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _safe_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^a-zA-Z0-9 _-]+", "", name)
    name = re.sub(r"\s+", "_", name)
    return name or "Student"


def _ensure_cert_table():
    """Ensure certificates table exists + required columns (non-destructive)."""
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


def _draw_soft_gradient_background(c: canvas.Canvas, w: float, h: float) -> None:
    """
    ReportLab has no true gradients by default, so we fake a premium gradient
    with thin horizontal bands.
    """
    top = Color(0.06, 0.20, 0.55)      # deep blue
    mid = Color(0.12, 0.55, 0.90)      # bright blue
    bottom = Color(0.94, 0.98, 1.00)   # very light blue

    steps = 70
    for i in range(steps):
        t = i / (steps - 1)
        # blend top->mid->bottom
        if t < 0.45:
            tt = t / 0.45
            r = top.red + (mid.red - top.red) * tt
            g = top.green + (mid.green - top.green) * tt
            b = top.blue + (mid.blue - top.blue) * tt
        else:
            tt = (t - 0.45) / 0.55
            r = mid.red + (bottom.red - mid.red) * tt
            g = mid.green + (bottom.green - mid.green) * tt
            b = mid.blue + (bottom.blue - mid.blue) * tt

        c.setFillColor(Color(r, g, b, alpha=0.16))
        y = (h * (1 - t))
        c.rect(0, y, w, h / steps + 2, fill=1, stroke=0)

    # Base wash so the page is never “white”
    c.setFillColor(Color(0.98, 0.99, 1.00))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Soft corner accents
    c.setFillColor(Color(0.12, 0.55, 0.90, alpha=0.10))
    c.circle(w * 0.88, h * 0.76, 110, fill=1, stroke=0)

    c.setFillColor(Color(0.98, 0.70, 0.25, alpha=0.10))  # gold tint
    c.circle(w * 0.12, h * 0.28, 90, fill=1, stroke=0)


def _draw_borders(c: canvas.Canvas, w: float, h: float) -> None:
    margin = 14 * mm

    # outer border
    c.setStrokeColor(Color(0.05, 0.12, 0.22, alpha=0.65))
    c.setLineWidth(2.4)
    c.roundRect(margin, margin, w - 2 * margin, h - 2 * margin, 16, stroke=1, fill=0)

    # inner border (gold-ish)
    c.setStrokeColor(Color(0.78, 0.60, 0.20, alpha=0.60))
    c.setLineWidth(1.2)
    c.roundRect(margin + 6, margin + 6, w - 2 * (margin + 6), h - 2 * (margin + 6), 14, stroke=1, fill=0)


def _draw_top_ribbon(c: canvas.Canvas, w: float, h: float) -> None:
    # Ribbon background
    ribbon_h = 24 * mm
    c.setFillColor(Color(0.06, 0.20, 0.55))
    c.roundRect(18 * mm, h - (18 * mm + ribbon_h), w - 36 * mm, ribbon_h, 14, fill=1, stroke=0)

    # Ribbon highlight line
    c.setFillColor(Color(0.12, 0.55, 0.90, alpha=0.25))
    c.roundRect(18 * mm, h - (18 * mm + 6), w - 36 * mm, 4, 6, fill=1, stroke=0)


def _draw_gold_seal(c: canvas.Canvas, x: float, y: float) -> None:
    # Outer ring
    c.setFillColor(Color(0.98, 0.78, 0.24, alpha=0.92))
    c.circle(x, y, 26, fill=1, stroke=0)
    # Inner
    c.setFillColor(Color(0.98, 0.90, 0.55, alpha=0.95))
    c.circle(x, y, 18, fill=1, stroke=0)
    # Center dot
    c.setFillColor(Color(0.78, 0.60, 0.20, alpha=0.85))
    c.circle(x, y, 3, fill=1, stroke=0)

    c.setFillColor(Color(0.20, 0.18, 0.12, alpha=0.80))
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x, y - 3, "CERTIFIED")


def _draw_watermark(c: canvas.Canvas, w: float, h: float) -> None:
    c.saveState()
    c.setFillColor(Color(0.06, 0.20, 0.55, alpha=0.05))
    c.translate(w / 2, h / 2)
    c.rotate(20)
    c.setFont("Helvetica-Bold", 86)
    c.drawCentredString(0, 0, "CHUMCRED")
    c.restoreState()


def _build_premium_landscape_certificate(full_name: str, out_path: str) -> str:
    _ensure_dir(os.path.dirname(out_path))

    w, h = landscape(A4)
    c = canvas.Canvas(out_path, pagesize=(w, h))

    # Premium background + styling
    _draw_soft_gradient_background(c, w, h)
    _draw_watermark(c, w, h)
    _draw_borders(c, w, h)
    _draw_top_ribbon(c, w, h)

    # Layout anchors
    left = 34 * mm
    right = w - 34 * mm
    cx = w / 2

    # Seal (top-right)
    _draw_gold_seal(c, right - 12, h - 34 * mm)

    # Brand inside ribbon
    c.setFillColor(Color(1, 1, 1))
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(cx, h - 33 * mm, "CHUMCRED ACADEMY")

    # Title
    c.setFillColor(Color(0.05, 0.12, 0.22))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(cx, h - 60 * mm, "CERTIFICATE OF COMPLETION")

    # Subtext
    c.setFillColor(Color(0.20, 0.26, 0.34))
    c.setFont("Helvetica", 14)
    c.drawCentredString(cx, h - 74 * mm, "This is to certify that")

    # Name highlight bar
    bar_w = min((right - left), 180 * mm)
    bar_h = 18 * mm
    bar_y = h - 100 * mm
    c.setFillColor(Color(0.12, 0.55, 0.90, alpha=0.10))
    c.roundRect(cx - bar_w / 2, bar_y - 8, bar_w, bar_h, 12, fill=1, stroke=0)

    # Name (auto-fit)
    name_font = "Helvetica-Bold"
    name_size = _fit_font_size(full_name.strip(), name_font, 46, 24, (right - left))
    c.setFillColor(Color(0.06, 0.08, 0.12))
    c.setFont(name_font, name_size)
    c.drawCentredString(cx, h - 96 * mm, full_name.strip())

    # Program lines
    c.setFillColor(Color(0.20, 0.26, 0.34))
    c.setFont("Helvetica", 14)
    c.drawCentredString(cx, h - 116 * mm, "has successfully completed the 6-week online training program")

    c.setFillColor(Color(0.05, 0.12, 0.22))
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(cx, h - 131 * mm, "AI Essentials — From Zero to Confident AI User")

    # Date
    issued_text = "Issued: " + datetime.now().strftime("%d %B %Y")
    c.setFillColor(Color(0.20, 0.26, 0.34))
    c.setFont("Helvetica", 12)
    c.drawCentredString(cx, h - 147 * mm, issued_text)

    # Signature area
    y_sig = 24 * mm
    c.setStrokeColor(Color(0.05, 0.12, 0.22, alpha=0.35))
    c.setLineWidth(1)
    c.line(left, y_sig + 18, left + 95 * mm, y_sig + 18)
    c.line(right - 95 * mm, y_sig + 18, right, y_sig + 18)

    c.setFillColor(Color(0.05, 0.12, 0.22))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y_sig, "Dr. Adekunle Adegbie")
    c.setFillColor(Color(0.20, 0.26, 0.34))
    c.setFont("Helvetica", 11)
    c.drawString(left, y_sig - 12, "Program Coordinator")

    c.setFillColor(Color(0.05, 0.12, 0.22))
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(right, y_sig, "Chumcred Academy")
    c.setFillColor(Color(0.20, 0.26, 0.34))
    c.setFont("Helvetica", 11)
    c.drawRightString(right, y_sig - 12, "Official Certificate")

    # Small footer note
    c.setFillColor(Color(0.20, 0.26, 0.34, alpha=0.75))
    c.setFont("Helvetica", 9)
    c.drawCentredString(cx, 12, "This certificate is issued by Chumcred Academy.")

    c.showPage()
    c.save()

    return os.path.abspath(out_path)


def issue_certificate(user_id: int, full_name: str) -> str:
    """
    Always generates the NEW premium landscape certificate and updates DB path.
    Uses timestamped filename so the old portrait file is never reused.
    """
    _ensure_cert_table()

    user_id = int(user_id)
    _ensure_dir(OUTPUT_DIR)

    safe_name = _safe_filename(full_name)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"CHUMCRED_PREMIUM_{safe_name}_{user_id}_{ts}.pdf"
    out_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))

    cert_path = _build_premium_landscape_certificate(full_name, out_path)
    issued_at = datetime.utcnow().isoformat()

    rec = get_certificate_record(user_id)

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
import os
import re
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import Color
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

from services.db import read_conn, write_txn

OUTPUT_DIR = os.getenv("CERT_OUTPUT_DIR", "/app/data/generated_certificates")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _safe_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^a-zA-Z0-9 _-]+", "", name)
    name = re.sub(r"\s+", "_", name)
    return name or "Student"


def _ensure_cert_table():
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


def _bg(c: canvas.Canvas, w: float, h: float) -> None:
    # base
    c.setFillColor(Color(0.98, 0.99, 1.00))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # soft bands
    c.setFillColor(Color(0.10, 0.40, 0.85, alpha=0.10))
    c.saveState(); c.translate(-w*0.15, h*0.10); c.rotate(-10)
    c.rect(0, h*0.55, w*1.4, h*0.18, fill=1, stroke=0)
    c.restoreState()

    c.setFillColor(Color(0.95, 0.55, 0.15, alpha=0.10))
    c.saveState(); c.translate(-w*0.10, h*0.02); c.rotate(-10)
    c.rect(0, h*0.32, w*1.4, h*0.14, fill=1, stroke=0)
    c.restoreState()

    c.setFillColor(Color(0.20, 0.75, 0.60, alpha=0.10))
    c.saveState(); c.translate(-w*0.06, -h*0.10); c.rotate(-10)
    c.rect(0, h*0.12, w*1.4, h*0.12, fill=1, stroke=0)
    c.restoreState()

    # accents
    c.setFillColor(Color(0.10, 0.40, 0.85, alpha=0.08))
    c.circle(w*0.90, h*0.80, 85, fill=1, stroke=0)
    c.setFillColor(Color(0.95, 0.55, 0.15, alpha=0.07))
    c.circle(w*0.12, h*0.25, 70, fill=1, stroke=0)


def _borders(c: canvas.Canvas, w: float, h: float) -> None:
    m = 14 * mm
    c.setStrokeColor(Color(0.08, 0.12, 0.20, alpha=0.70))
    c.setLineWidth(2.3)
    c.roundRect(m, m, w-2*m, h-2*m, 16, stroke=1, fill=0)

    c.setStrokeColor(Color(0.80, 0.62, 0.22, alpha=0.65))
    c.setLineWidth(1.2)
    c.roundRect(m+6, m+6, w-2*(m+6), h-2*(m+6), 14, stroke=1, fill=0)


def _watermark(c: canvas.Canvas, w: float, h: float) -> None:
    c.saveState()
    c.setFillColor(Color(0.10, 0.40, 0.85, alpha=0.05))
    c.translate(w/2, h/2)
    c.rotate(20)
    c.setFont("Helvetica-Bold", 84)
    c.drawCentredString(0, 0, "CHUMCRED")
    c.restoreState()


def _build_pdf(full_name: str, out_path: str) -> str:
    _ensure_dir(os.path.dirname(out_path))
    w, h = landscape(A4)
    c = canvas.Canvas(out_path, pagesize=(w, h))

    _bg(c, w, h)
    _watermark(c, w, h)
    _borders(c, w, h)

    left = 34 * mm
    right = w - 34 * mm
    cx = w / 2

    # marker so you can confirm THIS code is running
    c.setFillColor(Color(0.10, 0.12, 0.16, alpha=0.18))
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(right, h - 18 * mm, "PREMIUM_LANDSCAPE_V3")

    # header
    c.setFillColor(Color(0.05, 0.10, 0.18))
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(cx, h - 30 * mm, "CHUMCRED ACADEMY")

    c.setFillColor(Color(0.10, 0.40, 0.85))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(cx, h - 50 * mm, "CERTIFICATE OF COMPLETION")

    c.setFillColor(Color(0.20, 0.26, 0.34))
    c.setFont("Helvetica", 14)
    c.drawCentredString(cx, h - 66 * mm, "This is to certify that")

    # name
    max_width = right - left
    size = _fit_font_size(full_name, "Helvetica-Bold", 48, 24, max_width)
    c.setFillColor(Color(0.10, 0.40, 0.85, alpha=0.10))
    c.roundRect(cx - min(max_width, 180*mm)/2, h - 92*mm, min(max_width, 180*mm), 18*mm, 12, fill=1, stroke=0)

    c.setFillColor(Color(0.06, 0.08, 0.12))
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(cx, h - 88 * mm, full_name)

    # body
    c.setFillColor(Color(0.20, 0.26, 0.34))
    c.setFont("Helvetica", 14)
    c.drawCentredString(cx, h - 110 * mm, "has successfully completed the 6-week online training program")

    c.setFillColor(Color(0.05, 0.10, 0.18))
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(cx, h - 124 * mm, "AI Essentials — From Zero to Confident AI User")

    # date
    issued_text = "Issued: " + datetime.now().strftime("%d %B %Y")
    c.setFillColor(Color(0.20, 0.26, 0.34))
    c.setFont("Helvetica", 12)
    c.drawCentredString(cx, h - 140 * mm, issued_text)

    # signatures
    y_sig = 24 * mm
    c.setStrokeColor(Color(0.05, 0.10, 0.18, alpha=0.35))
    c.setLineWidth(1)
    c.line(left, y_sig + 18, left + 95 * mm, y_sig + 18)
    c.line(right - 95 * mm, y_sig + 18, right, y_sig + 18)

    c.setFillColor(Color(0.05, 0.10, 0.18))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y_sig, "Dr. Adekunle Adegbie")
    c.setFillColor(Color(0.20, 0.26, 0.34))
    c.setFont("Helvetica", 11)
    c.drawString(left, y_sig - 12, "Program Coordinator")

    c.setFillColor(Color(0.05, 0.10, 0.18))
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(right, y_sig, "Chumcred Academy")
    c.setFillColor(Color(0.20, 0.26, 0.34))
    c.setFont("Helvetica", 11)
    c.drawRightString(right, y_sig - 12, "Official Certificate")

    c.showPage()
    c.save()
    return os.path.abspath(out_path)


def issue_certificate(user_id: int, full_name: str) -> str:
    """
    ALWAYS generate a brand-new premium landscape certificate and update DB.
    """
    _ensure_cert_table()
    user_id = int(user_id)
    _ensure_dir(OUTPUT_DIR)

    safe = _safe_filename(full_name)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"PREMIUM_LANDSCAPE_V3_{safe}_{user_id}_{ts}.pdf"
    out_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))

    cert_path = _build_pdf(full_name.strip(), out_path)
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
import os
import re
from datetime import datetime
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import Color

from pypdf import PdfReader, PdfWriter

from services.db import read_conn, write_txn


# ✅ persistent folder (Railway volume should be mounted to /app/data)
OUTPUT_DIR = os.getenv("CERT_OUTPUT_DIR", "/app/data/generated_certificates")

# Template locations to try (works in local + Railway)
TEMPLATE_CANDIDATES = [
    os.getenv("CERT_TEMPLATE_PATH", "").strip(),
    "/app/assets/chumcred_certificate_template.pdf",
    "assets/chumcred_certificate_template.pdf",
    "./assets/chumcred_certificate_template.pdf",
    "chumcred_certificate_template.pdf",
]

# Background color behind name/date on your template (safe “paper” tone)
BG = Color(244 / 255, 249 / 255, 249 / 255)


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


def _find_template_path() -> str:
    for p in TEMPLATE_CANDIDATES:
        if not p:
            continue
        p_abs = os.path.abspath(p)
        if os.path.exists(p_abs):
            return p_abs
    raise FileNotFoundError(
        "Certificate template PDF not found. Expected one of:\n"
        "- /app/assets/chumcred_certificate_template.pdf (Railway)\n"
        "- assets/chumcred_certificate_template.pdf (repo)\n"
        "OR set CERT_TEMPLATE_PATH env var."
    )


def _fit_font_size(text: str, font: str, max_size: int, min_size: int, max_width: float) -> int:
    size = max_size
    while size > min_size:
        if stringWidth(text, font, size) <= max_width:
            return size
        size -= 1
    return min_size


def _make_overlay_pdf(page_w: float, page_h: float, full_name: str, issued_text: str) -> bytes:
    """
    Create a one-page transparent overlay PDF that covers the old name/date area and
    writes the new name/date in the right spot.

    NOTE: Coordinates are tuned to your template PDF you uploaded.
    If you later change the template design, we may need to re-tune.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))

    # These positions are relative (works robustly across the same template)
    # Name: centered in the middle band
    name_center_x = page_w / 2
    name_y = page_h * 0.58

    # Issued date: centered below name
    issued_center_x = page_w / 2
    issued_y = page_h * 0.47

    # Cover old text area (small “paper color” rectangles)
    c.setFillColor(BG)
    c.setStrokeColor(BG)

    # name cover box
    c.rect(name_center_x - 260, name_y - 18, 520, 55, fill=1, stroke=0)
    # issued cover box
    c.rect(issued_center_x - 210, issued_y - 12, 420, 30, fill=1, stroke=0)

    # Write name (auto-fit)
    font_name = "Helvetica-Bold"
    font_size = _fit_font_size(full_name, font_name, max_size=36, min_size=18, max_width=560)

    c.setFillColor(Color(0.07, 0.10, 0.16))
    c.setFont(font_name, font_size)
    c.drawCentredString(name_center_x, name_y, full_name)

    # Write issued date
    c.setFont("Helvetica", 16)
    c.drawCentredString(issued_center_x, issued_y, issued_text)

    c.showPage()
    c.save()
    return buf.getvalue()


def _build_certificate_pdf_from_template(full_name: str, out_path: str) -> str:
    """
    Generates certificate using the uploaded template PDF as background.
    """
    template_path = _find_template_path()
    _ensure_dir(os.path.dirname(out_path))

    reader = PdfReader(template_path)
    template_page = reader.pages[0]

    page_w = float(template_page.mediabox.width)
    page_h = float(template_page.mediabox.height)

    issued_text = "Issued: " + datetime.now().strftime("%B %d, %Y")

    overlay_bytes = _make_overlay_pdf(page_w, page_h, full_name.strip(), issued_text)
    overlay_reader = PdfReader(BytesIO(overlay_bytes))
    overlay_page = overlay_reader.pages[0]

    template_page.merge_page(overlay_page)

    writer = PdfWriter()
    writer.add_page(template_page)

    with open(out_path, "wb") as f:
        writer.write(f)

    return os.path.abspath(out_path)


def issue_certificate(user_id: int, full_name: str) -> str:
    """
    Generates a certificate PDF using the TEMPLATE background,
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

    # Generate PDF from template
    cert_path = _build_certificate_pdf_from_template(full_name, out_path)
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
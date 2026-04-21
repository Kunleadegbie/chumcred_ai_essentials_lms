import os
import re
from datetime import datetime
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from reportlab.pdfbase.pdfmetrics import stringWidth

from pypdf import PdfReader, PdfWriter

from services.db import read_conn, write_txn


# ✅ Persistent folder on Railway (mount volume to /app/data)
OUTPUT_DIR = os.getenv("CERT_OUTPUT_DIR", "/app/data/generated_certificates")

# ✅ Template file path (put the sample PDF here)
TEMPLATE_PATH = os.getenv("CERT_TEMPLATE_PATH", "assets/chumcred_certificate_template.pdf")

# Background color behind the name/date on your template (sampled from your PDF)
BG = Color(244/255, 249/255, 249/255)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _safe_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^a-zA-Z0-9 _-]+", "", name)
    name = re.sub(r"\s+", "_", name)
    return name or "Student"


def has_certificate(user_id: int) -> bool:
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM certificates WHERE user_id=? LIMIT 1", (int(user_id),))
        return cur.fetchone() is not None


def get_certificate_record(user_id: int):
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, user_id, issued_at, certificate_path FROM certificates "
            "WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (int(user_id),),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def _fit_font_size(text: str, font: str, max_size: float, min_size: float, max_width: float) -> float:
    """Reduce font size until text fits inside max_width."""
    size = max_size
    while size > min_size:
        if stringWidth(text, font, size) <= max_width:
            return size
        size -= 1
    return min_size


def _overlay_pdf(page_width: float, page_height: float, full_name: str, issued_text: str) -> bytes:
    """
    Create an overlay PDF that:
    - paints background rectangles over the old name/date
    - writes the new name/date in the exact template positions
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_width, page_height))

    # Coordinates below are based on your template PDF text positions.
    # NOTE: ReportLab uses bottom-left origin. These were calibrated to your sample.
    # Name area (centered)
    name_bbox = {
        "x0": 268.9,
        "y0": 595.2756 - 369.824,   # convert from top-left bbox to bottom-left
        "x1": 573.0,
        "y1": 595.2756 - 325.760,
    }
    # Issued area
    issued_bbox = {
        "x0": 337.34,
        "y0": 595.2756 - 469.784,
        "x1": 504.54,
        "y1": 595.2756 - 447.800,
    }

    # Draw background rectangles (match template background)
    c.setFillColor(BG)
    c.setStrokeColor(BG)

    # Slight padding to fully cover old text
    pad = 6
    c.rect(
        name_bbox["x0"] - pad,
        name_bbox["y0"] - pad,
        (name_bbox["x1"] - name_bbox["x0"]) + (pad * 2),
        (name_bbox["y1"] - name_bbox["y0"]) + (pad * 2),
        fill=1,
        stroke=0,
    )

    c.rect(
        issued_bbox["x0"] - pad,
        issued_bbox["y0"] - pad,
        (issued_bbox["x1"] - issued_bbox["x0"]) + (pad * 2),
        (issued_bbox["y1"] - issued_bbox["y0"]) + (pad * 2),
        fill=1,
        stroke=0,
    )

    # Write new name (centered in the same box)
    font_name = "Helvetica-Bold"
    max_font = 32
    min_font = 18
    max_width = (name_bbox["x1"] - name_bbox["x0"]) + 20  # allow a bit more
    size = _fit_font_size(full_name, font_name, max_font, min_font, max_width)

    c.setFillColor(Color(0.07, 0.10, 0.16))  # dark text similar to template
    c.setFont(font_name, size)

    name_center_x = (name_bbox["x0"] + name_bbox["x1"]) / 2
    # baseline approx: use lower part of bbox + offset
    name_y = name_bbox["y0"] + ((name_bbox["y1"] - name_bbox["y0"]) * 0.30)
    c.drawCentredString(name_center_x, name_y, full_name)

    # Write issued date (same style as template)
    c.setFont("Helvetica", 16)
    issued_center_x = (issued_bbox["x0"] + issued_bbox["x1"]) / 2
    issued_y = issued_bbox["y0"] + 2
    c.drawCentredString(issued_center_x, issued_y, issued_text)

    c.showPage()
    c.save()

    return buf.getvalue()


def _build_certificate_from_template(full_name: str, out_path: str) -> str:
    """
    Merge template PDF + overlay PDF (name/date) -> final out_path
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Certificate template not found: {TEMPLATE_PATH}. "
            f"Place it at assets/chumcred_certificate_template.pdf or set CERT_TEMPLATE_PATH."
        )

    _ensure_dir(os.path.dirname(out_path))

    # Read template
    template_reader = PdfReader(TEMPLATE_PATH)
    template_page = template_reader.pages[0]

    page_width = float(template_page.mediabox.width)
    page_height = float(template_page.mediabox.height)

    issued_text = "Issued: " + datetime.now().strftime("%B %d, %Y")

    # Create overlay bytes
    overlay_bytes = _overlay_pdf(page_width, page_height, full_name, issued_text)
    overlay_reader = PdfReader(BytesIO(overlay_bytes))
    overlay_page = overlay_reader.pages[0]

    # Merge
    writer = PdfWriter()
    template_page.merge_page(overlay_page)
    writer.add_page(template_page)

    with open(out_path, "wb") as f:
        writer.write(f)

    return os.path.abspath(out_path)


def issue_certificate(user_id: int, full_name: str) -> str:
    """
    Generate certificate using Chumcred template.
    - Saves to /app/data/generated_certificates (persistent)
    - Stores absolute certificate_path in DB
    - If record exists but file missing, regenerates and updates record
    """
    user_id = int(user_id)
    safe_name = _safe_filename(full_name)
    filename = f"certificate_{safe_name}_{user_id}.pdf"
    out_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))

    # If record exists
    rec = get_certificate_record(user_id)
    if rec:
        existing_path = rec.get("certificate_path")
        if existing_path and os.path.exists(existing_path):
            return existing_path

        # regenerate and update DB
        cert_path = _build_certificate_from_template(full_name, out_path)
        issued_at = datetime.utcnow().isoformat()

        with write_txn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE certificates SET issued_at=?, certificate_path=? WHERE id=?",
                (issued_at, cert_path, int(rec["id"])),
            )
            conn.commit()

        return cert_path

    # No record: create PDF + insert row
    cert_path = _build_certificate_from_template(full_name, out_path)
    issued_at = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO certificates (user_id, issued_at, certificate_path) VALUES (?, ?, ?)",
            (user_id, issued_at, cert_path),
        )
        conn.commit()

    return cert_path
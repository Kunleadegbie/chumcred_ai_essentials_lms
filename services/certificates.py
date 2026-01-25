import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from services.db import read_conn, write_txn


OUTPUT_DIR = os.getenv("CERT_OUTPUT_DIR", "generated_certificates")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def has_certificate(user_id: int) -> bool:
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM certificates WHERE user_id=? LIMIT 1", (int(user_id),))
        return cur.fetchone() is not None


def get_certificate_record(user_id: int):
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, user_id, issued_at, certificate_path FROM certificates WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (int(user_id),),
        )
        row = cur.fetchone()
        if not row:
            return None
        # sqlite3.Row safe conversion
        return dict(row)


def _build_certificate_pdf(full_name: str, filename: str) -> str:
    _ensure_dir(OUTPUT_DIR)
    out_path = os.path.join(OUTPUT_DIR, filename)

    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4

    # --- Simple professional layout (Option B) ---
    # Border
    margin = 15 * mm
    c.setLineWidth(2)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # Header
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 60 * mm, "CHUMCRED ACADEMY")

    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 72 * mm, "CERTIFICATE OF COMPLETION")

    # Body
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 95 * mm, "This is to certify that")

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 112 * mm, full_name.strip())

    c.setFont("Helvetica", 12)
    c.drawCentredString(
        width / 2,
        height - 130 * mm,
        "has successfully completed the 6-week online training program",
    )

    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(
        width / 2,
        height - 145 * mm,
        "AI Essentials — From Zero to Confident AI User",
    )

    # Footer (date)
    issued = datetime.utcnow().strftime("%d %b %Y")
    c.setFont("Helvetica", 11)
    c.drawString(margin + 10 * mm, margin + 18 * mm, f"Issued: {issued}")

    c.setFont("Helvetica", 11)
    c.drawRightString(width - (margin + 10 * mm), margin + 18 * mm, "Chumcred Academy")

    c.showPage()
    c.save()

    return out_path


def issue_certificate(user_id: int, full_name: str) -> str:
    """
    Creates certificate PDF + stores record.
    Returns certificate_path.
    Safe to call multiple times: will not duplicate if already issued.
    """
    user_id = int(user_id)

    if has_certificate(user_id):
        rec = get_certificate_record(user_id)
        return rec["certificate_path"]

    # Use stable filename
    safe_name = "".join(ch for ch in full_name if ch.isalnum() or ch in (" ", "-", "_")).strip()
    safe_name = safe_name.replace(" ", "_") or f"user_{user_id}"
    filename = f"certificate_{safe_name}_{user_id}.pdf"

    cert_path = _build_certificate_pdf(full_name=full_name, filename=filename)
    issued_at = datetime.utcnow().isoformat()

    with write_txn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO certificates (user_id, issued_at, certificate_path) VALUES (?, ?, ?)",
            (user_id, issued_at, cert_path),
        )

    return cert_path

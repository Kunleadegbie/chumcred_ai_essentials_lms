import os
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

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


def _build_certificate_pdf(full_name: str, out_path: str) -> str:
    """
    Generates certificate in the SAME format as your template PDF content:
    CERTIFICATE OF COMPLETION
    This certifies that
    <Full Name>
    has successfully completed the AI Essentials Program
    Chumcred Academy
    Issued: <date>
    Dr. Adekunle Adegbie
    Program Coordinator
    """
    _ensure_dir(os.path.dirname(out_path))

    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2, height - 120, "CERTIFICATE OF COMPLETION")

    # Subtitle
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 165, "This certifies that")

    # Name
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 215, full_name.strip())

    # Program line
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 255, "has successfully completed the AI Essentials Program")

    # Academy
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 295, "Chumcred Academy")

    # Issued date
    issued = datetime.now().strftime("%B %d, %Y")
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 340, f"Issued: {issued}")

    # Coordinator name
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 395, "Dr. Adekunle Adegbie")

    # Coordinator title
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 415, "Program Coordinator")

    c.showPage()
    c.save()

    return os.path.abspath(out_path)


def issue_certificate(user_id: int, full_name: str) -> str:
    """
    Generates a certificate PDF (ReportLab only),
    saves it to OUTPUT_DIR, and stores absolute path in DB.
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

    # Generate PDF
    cert_path = _build_certificate_pdf(full_name, out_path)
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
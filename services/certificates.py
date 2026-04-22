import os
import re
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

from services.db import read_conn, write_txn

# =========================================================
# CONFIG
# =========================================================
OUTPUT_DIR = os.getenv("CERT_OUTPUT_DIR", "/app/data/generated_certificates")
BG_IMG_PATH = os.getenv("CERT_BG_IMG_PATH", "assets/certificate_bg.png")

PROGRAM_NAME = "AI Essentials — From Zero to Confident AI User"
ACADEMY_NAME = "Chumcred Academy"
COORDINATOR_NAME = "Dr. Adekunle Adegbie"
COORDINATOR_TITLE = "Program Coordinator"

# Theme colors
TEXT_DARK = colors.HexColor("#101A2F")
TEXT_SOFT = colors.HexColor("#1E2435")
TEXT_MUTED = colors.HexColor("#3B465C")
ACCENT = colors.HexColor("#1F8D84")


# =========================================================
# HELPERS
# =========================================================
def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _safe_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^a-zA-Z0-9 _-]+", "", name)
    name = re.sub(r"\s+", "_", name)
    return name or "Student"


def _fit_font_size(text: str, font: str, max_size: int, min_size: int, max_width: float) -> int:
    size = max_size
    while size >= min_size:
        if stringWidth(text, font, size) <= max_width:
            return size
        size -= 1
    return min_size


def _draw_centered(c, text, y, font_name="Helvetica", font_size=16, color=TEXT_DARK):
    c.setFillColor(color)
    c.setFont(font_name, font_size)
    page_width = landscape(A4)[0]
    c.drawCentredString(page_width / 2, y, text)


def _resolve_bg_path() -> str:
    candidates = [
        BG_IMG_PATH,
        os.path.join("/app", BG_IMG_PATH),
        "/app/assets/certificate_bg.png",
        "/app/data/certificate_bg.png",
        "assets/certificate_bg.png",
        "./assets/certificate_bg.png",
    ]
    for p in candidates:
        p = (p or "").strip()
        if p and os.path.exists(p):
            return p

    raise FileNotFoundError(
        "Certificate background PNG not found. "
        "Save the blank template as assets/certificate_bg.png "
        "or set CERT_BG_IMG_PATH."
    )


# =========================================================
# DATABASE HELPERS
# =========================================================
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
        cur.execute(
            "SELECT 1 FROM certificates WHERE user_id=? LIMIT 1",
            (int(user_id),)
        )
        return cur.fetchone() is not None


def get_certificate_record(user_id: int):
    _ensure_cert_table()
    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, issued_at, certificate_path
            FROM certificates
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(user_id),),
        )
        row = cur.fetchone()
        return dict(row) if row else None


# =========================================================
# CERTIFICATE GENERATOR
# =========================================================
def _build_certificate_pdf(full_name: str, out_path: str, certificate_id: str = "") -> str:
    _ensure_dir(os.path.dirname(out_path))

    w, h = landscape(A4)
    c = canvas.Canvas(out_path, pagesize=(w, h))

    # Background template
    bg_path = _resolve_bg_path()
    bg = ImageReader(bg_path)
    c.drawImage(bg, 0, 0, width=w, height=h, mask="auto")

    issued_date = datetime.now().strftime("%B %d, %Y")

    # -----------------------------
    # Main certificate body
    # -----------------------------
    _draw_centered(
        c,
        "This certifies that",
        y=h * 0.60,
        font_name="Helvetica",
        font_size=22,
        color=TEXT_SOFT,
    )

    # Student name
    max_name_width = w * 0.72
    name_size = _fit_font_size(
        full_name,
        font="Helvetica-Bold",
        max_size=34,
        min_size=22,
        max_width=max_name_width,
    )
    _draw_centered(
        c,
        full_name,
        y=h * 0.50,
        font_name="Helvetica-Bold",
        font_size=name_size,
        color=TEXT_DARK,
    )

    _draw_centered(
        c,
        "has successfully completed the 6-week online training program",
        y=h * 0.43,
        font_name="Helvetica",
        font_size=18,
        color=TEXT_SOFT,
    )

    _draw_centered(
        c,
        PROGRAM_NAME,
        y=h * 0.36,
        font_name="Helvetica-Bold",
        font_size=20,
        color=TEXT_DARK,
    )

    # Optional thin accent line
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.2)
    c.line(w * 0.34, h * 0.325, w * 0.66, h * 0.325)

    # Academy line
    _draw_centered(
        c,
        ACADEMY_NAME,
        y=h * 0.27,
        font_name="Helvetica-Bold",
        font_size=16,
        color=TEXT_DARK,
    )

    # Date
    _draw_centered(
        c,
        f"Issued: {issued_date}",
        y=h * 0.19,
        font_name="Helvetica",
        font_size=15,
        color=TEXT_MUTED,
    )

    # Signature block
    _draw_centered(
        c,
        COORDINATOR_NAME,
        y=h * 0.14,
        font_name="Helvetica-Bold",
        font_size=14,
        color=TEXT_DARK,
    )

    _draw_centered(
        c,
        COORDINATOR_TITLE,
        y=h * 0.10,
        font_name="Helvetica",
        font_size=13,
        color=TEXT_MUTED,
    )

    # Certificate ID at the bottom
    if certificate_id:
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica", 10)
        c.drawCentredString(w / 2, h * 0.055, f"Certificate ID: {certificate_id}")

    c.showPage()
    c.save()
    return os.path.abspath(out_path)


def issue_certificate(user_id: int, full_name: str) -> str:
    """
    Generate or regenerate certificate for a student.
    Saves the latest certificate path in the certificates table.
    """
    _ensure_cert_table()

    user_id = int(user_id)
    full_name = (full_name or "").strip()
    if not full_name:
        full_name = "Student"

    _ensure_dir(OUTPUT_DIR)

    safe_name = _safe_filename(full_name)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    certificate_id = f"CHUM-{user_id}-{datetime.utcnow().strftime('%Y%m%d')}"

    filename = f"certificate_{safe_name}_{user_id}_{ts}.pdf"
    out_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))

    cert_path = _build_certificate_pdf(
        full_name=full_name,
        out_path=out_path,
        certificate_id=certificate_id,
    )
    issued_at = datetime.utcnow().isoformat()

    existing = get_certificate_record(user_id)

    with write_txn() as conn:
        cur = conn.cursor()
        if existing:
            cur.execute(
                """
                UPDATE certificates
                SET issued_at=?, certificate_path=?
                WHERE id=?
                """,
                (issued_at, cert_path, int(existing["id"])),
            )
        else:
            cur.execute(
                """
                INSERT INTO certificates (user_id, issued_at, certificate_path)
                VALUES (?, ?, ?)
                """,
                (user_id, issued_at, cert_path),
            )
        conn.commit()

    return cert_path
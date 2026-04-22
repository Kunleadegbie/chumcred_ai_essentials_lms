import os
import re
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader

from services.db import read_conn, write_txn

# Persistent folder (Railway volume should be mounted to /app/data)
OUTPUT_DIR = os.getenv("CERT_OUTPUT_DIR", "/app/data/generated_certificates")

# Background image (default: repo asset)
BG_IMG_PATH = os.getenv("CERT_BG_IMG_PATH", "assets/certificate_bg.png")

# ---- TUNING ----
NAME_Y_FRAC = 0.54
DATE_Y_FRAC = 0.40
NAME_MAX_WIDTH_FRAC = 0.70


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


def _resolve_bg_path() -> str:
    # ✅ includes /app/data fallback too
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
        "Make sure you have assets/certificate_bg.png (blank template) committed, "
        "or set CERT_BG_IMG_PATH."
    )


def _build_certificate_pdf(full_name: str, out_path: str) -> str:
    _ensure_dir(os.path.dirname(out_path))

    w, h = landscape(A4)
    c = canvas.Canvas(out_path, pagesize=(w, h))

    # Draw PNG background full-page
    bg_path = _resolve_bg_path()
    bg = ImageReader(bg_path)
    c.drawImage(bg, 0, 0, width=w, height=h, mask="auto")

    cx = w / 2

    # Name
    name_font = "Helvetica-Bold"
    max_name_width = w * NAME_MAX_WIDTH_FRAC
    name_size = _fit_font_size(full_name, name_font, max_size=42, min_size=18, max_width=max_name_width)
    c.setFont(name_font, name_size)
    c.drawCentredString(cx, h * NAME_Y_FRAC, full_name)

    # Issued date
    issued_text = "Issued: " + datetime.now().strftime("%B %d, %Y")
    c.setFont("Helvetica", 16)
    c.drawCentredString(cx, h * DATE_Y_FRAC, issued_text)

    # ✅ Invisible marker now includes which background file was used
    c.setFont("Helvetica", 1)
    c.drawString(2, 2, f"BG_CERT_V2|BGFILE={os.path.basename(bg_path)}")

    c.showPage()
    c.save()
    return os.path.abspath(out_path)


def issue_certificate(user_id: int, full_name: str) -> str:
    """Always generates a new certificate using the PNG background and updates DB."""
    _ensure_cert_table()
    user_id = int(user_id)
    _ensure_dir(OUTPUT_DIR)

    safe = _safe_filename(full_name)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"certificate_{safe}_{user_id}_{ts}.pdf"
    out_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))

    cert_path = _build_certificate_pdf(full_name.strip(), out_path)
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
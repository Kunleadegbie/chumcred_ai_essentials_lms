from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from datetime import datetime
import os


def generate_certificate(student_name):

    file_name = "chumcred_certificate.pdf"

    c = canvas.Canvas(file_name, pagesize=landscape(A4))
    width, height = landscape(A4)

    # --------------------------
    # Background
    # --------------------------
    c.setFillColor(HexColor("#F4FAF9"))
    c.rect(0, 0, width, height, fill=1)

    # --------------------------
    # Decorative borders
    # --------------------------
    c.setStrokeColor(HexColor("#0F766E"))
    c.setLineWidth(6)
    c.rect(30, 30, width-60, height-60)

    c.setStrokeColor(HexColor("#14B8A6"))
    c.setLineWidth(2)
    c.rect(50, 50, width-100, height-100)

    # --------------------------
    # Logo detection
    # --------------------------
    logo1 = os.path.join("assets", "chumcred_academy_logo.png")
    logo2 = os.path.join("assets", "logo.png")

    logo_path = None

    if os.path.isfile(logo1):
        logo_path = logo1
    elif os.path.isfile(logo2):
        logo_path = logo2

    if logo_path:
        c.drawImage(
            logo_path,
            width/2 - 80,
            height - 150,
            width=160,
            preserveAspectRatio=True,
            mask='auto'
        )

    # --------------------------
    # Title
    # --------------------------
    c.setFillColor(HexColor("#111827"))
    c.setFont("Helvetica-Bold", 36)

    c.drawCentredString(
        width/2,
        height - 220,
        "CERTIFICATE OF COMPLETION"
    )

    # --------------------------
    # Certificate body
    # --------------------------
    c.setFont("Helvetica", 18)

    c.drawCentredString(
        width/2,
        height - 300,
        "This certifies that"
    )

    c.setFont("Helvetica-Bold", 32)

    c.drawCentredString(
        width/2,
        height - 350,
        student_name
    )

    c.setFont("Helvetica", 18)

    c.drawCentredString(
        width/2,
        height - 400,
        "has successfully completed the AI Essentials Program"
    )

    c.setFont("Helvetica-Bold", 22)

    c.drawCentredString(
        width/2,
        height - 440,
        "Chumcred Academy"
    )

    # --------------------------
    # Date
    # --------------------------
    today = datetime.now().strftime("%B %d, %Y")

    c.setFont("Helvetica", 16)

    c.drawCentredString(
        width/2,
        height - 480,
        f"Issued: {today}"
    )

    # --------------------------
    # Signature section
    # (moved further down to avoid overlap)
    # --------------------------
    c.setFont("Helvetica-Bold", 18)

    c.drawCentredString(
        width/2,
        110,
        "Dr. Adekunle Adegbie"
    )

    c.setFont("Helvetica", 16)

    c.drawCentredString(
        width/2,
        85,
        "Program Coordinator"
    )

    # --------------------------
    # Save PDF
    # --------------------------
    c.save()

    with open(file_name, "rb") as f:
        pdf = f.read()

    return pdf
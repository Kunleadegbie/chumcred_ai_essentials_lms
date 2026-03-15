from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from datetime import datetime
import os


def generate_certificate(student_name):

    file_name = "chumcred_certificate.pdf"

    c = canvas.Canvas(file_name, pagesize=landscape(A4))
    width, height = landscape(A4)

    # ------------------------------------------------
    # Background
    # ------------------------------------------------
    c.setFillColor(HexColor("#F4FAF9"))
    c.rect(0, 0, width, height, fill=1)

    # ------------------------------------------------
    # Decorative Borders
    # ------------------------------------------------
    c.setStrokeColor(HexColor("#0F766E"))
    c.setLineWidth(6)
    c.rect(30, 30, width - 60, height - 60)

    c.setStrokeColor(HexColor("#14B8A6"))
    c.setLineWidth(2)
    c.rect(50, 50, width - 100, height - 100)

    # ------------------------------------------------
    # LOGO
    # ------------------------------------------------
    logo_path = os.path.abspath("assets/logo.png")

    if os.path.exists(logo_path):

        logo = ImageReader(logo_path)

        c.drawImage(
            logo,
            width/2 - 60,
            height - 140,
            width=120,
            preserveAspectRatio=True,
            mask="auto"
        )

    # ------------------------------------------------
    # Title
    # ------------------------------------------------
    c.setFillColor(HexColor("#111827"))
    c.setFont("Helvetica-Bold", 38)
    c.drawCentredString(width/2, height - 220, "CERTIFICATE OF COMPLETION")

    # ------------------------------------------------
    # Intro Text
    # ------------------------------------------------
    c.setFont("Helvetica", 20)
    c.drawCentredString(width/2, height - 300, "This certifies that")

    # ------------------------------------------------
    # Student Name
    # ------------------------------------------------
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(width/2, height - 360, student_name)

    # ------------------------------------------------
    # Completion Text
    # ------------------------------------------------
    c.setFont("Helvetica", 20)
    c.drawCentredString(
        width/2,
        height - 420,
        "has successfully completed the AI Essentials Program"
    )

    # ------------------------------------------------
    # Academy Name
    # ------------------------------------------------
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2, height - 480, "Chumcred Academy")

    # ------------------------------------------------
    # Date
    # ------------------------------------------------
    today = datetime.now().strftime("%B %d, %Y")

    c.setFont("Helvetica", 18)
    c.drawCentredString(width/2, height - 520, f"Issued: {today}")

    # ------------------------------------------------
    # Signature Section
    # ------------------------------------------------
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, 160, "Dr. Adekunle Adegbie")

    c.setFont("Helvetica", 18)
    c.drawCentredString(width/2, 130, "Program Coordinator")

    # ------------------------------------------------
    # Save PDF
    # ------------------------------------------------
    c.save()

    with open(file_name, "rb") as f:
        pdf = f.read()

    return pdf
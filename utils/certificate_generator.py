from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from datetime import datetime
import os


def generate_certificate(student_name):

    file_name = "chumcred_certificate.pdf"

    c = canvas.Canvas(file_name, pagesize=landscape(A4))
    width, height = landscape(A4)

    # Background
    c.setFillColor(HexColor("#F4FAF9"))
    c.rect(0, 0, width, height, fill=1)

    # Borders
    c.setStrokeColor(HexColor("#0F766E"))
    c.setLineWidth(6)
    c.rect(30, 30, width-60, height-60)

    c.setStrokeColor(HexColor("#14B8A6"))
    c.setLineWidth(2)
    c.rect(50, 50, width-100, height-100)

    # ---- Locate logo reliably ----
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    logo_path = os.path.join(project_root, "assets", "logo.png")

    if os.path.exists(logo_path):
        c.drawImage(
            logo_path,
            width/2 - 80,
            height - 160,
            width=160,
            preserveAspectRatio=True,
            mask="auto"
        )

    # Title
    c.setFillColor(HexColor("#111827"))
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width/2, height - 220, "CERTIFICATE OF COMPLETION")

    # Body
    c.setFont("Helvetica", 18)
    c.drawCentredString(width/2, height - 300, "This certifies that")

    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width/2, height - 350, student_name)

    c.setFont("Helvetica", 18)
    c.drawCentredString(width/2, height - 400,
                        "has successfully completed the AI Essentials Program")

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width/2, height - 440, "Chumcred Academy")

    # Date
    today = datetime.now().strftime("%B %d, %Y")
    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, height - 485, f"Issued: {today}")

    # Signature (moved lower)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, 100, "Dr. Adekunle Adegbie")

    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, 75, "Program Coordinator")

    c.save()

    with open(file_name, "rb") as f:
        pdf = f.read()

    return pdf
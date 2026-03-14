from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from datetime import datetime


def generate_certificate(student_name):

    file_name = "chumcred_certificate.pdf"

    c = canvas.Canvas(file_name, pagesize=landscape(A4))
    width, height = landscape(A4)

    # -------------------------
    # Background
    # -------------------------
    c.setFillColor(HexColor("#F4FAF9"))
    c.rect(0, 0, width, height, fill=1)

    # -------------------------
    # Decorative borders
    # -------------------------
    c.setStrokeColor(HexColor("#0F766E"))  # Chumcred teal
    c.setLineWidth(6)
    c.rect(30, 30, width-60, height-60)

    c.setStrokeColor(HexColor("#14B8A6"))  # light teal accent
    c.setLineWidth(2)
    c.rect(50, 50, width-100, height-100)

    # -------------------------
    # Logo
    # -------------------------
    logo_path = "assets/chumcred_academy_logo.png"

    c.drawImage(
        logo_path,
        width/2 - 90,
        height - 150,
        width=180,
        preserveAspectRatio=True,
        mask='auto'
    )

    # -------------------------
    # Title
    # -------------------------
    c.setFillColor(HexColor("#111827"))
    c.setFont("Helvetica-Bold", 34)

    c.drawCentredString(
        width/2,
        height - 210,
        "CERTIFICATE OF COMPLETION"
    )

    # -------------------------
    # Body
    # -------------------------
    c.setFont("Helvetica", 18)

    c.drawCentredString(
        width/2,
        height - 270,
        "This certifies that"
    )

    # Student name
    c.setFont("Helvetica-Bold", 30)

    c.drawCentredString(
        width/2,
        height - 320,
        student_name
    )

    c.setFont("Helvetica", 18)

    c.drawCentredString(
        width/2,
        height - 370,
        "has successfully completed the AI Essentials Program"
    )

    c.setFont("Helvetica-Bold", 22)

    c.drawCentredString(
        width/2,
        height - 420,
        "Chumcred Academy"
    )

    # -------------------------
    # Date
    # -------------------------
    today = datetime.now().strftime("%B %d, %Y")

    c.setFont("Helvetica", 16)

    c.drawCentredString(
        width/2,
        height - 460,
        f"Issued: {today}"
    )

    # -------------------------
    # Signature
    # -------------------------
    c.setFont("Helvetica-Bold", 18)

    c.drawString(
        width/2 - 200,
        130,
        "Dr. Adekunle Adegbie"
    )

    c.setFont("Helvetica", 16)

    c.drawString(
        width/2 - 200,
        105,
        "Program Coordinator"
    )

    # -------------------------
    # Save
    # -------------------------
    c.save()

    with open(file_name, "rb") as f:
        pdf = f.read()

    return pdf
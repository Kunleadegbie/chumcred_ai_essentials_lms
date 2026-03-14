from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
import io
from datetime import datetime

def generate_certificate(student_name):

    buffer = io.BytesIO()

    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    width, height = landscape(A4)

    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width/2, height-120, "Certificate of Participation")

    c.setFont("Helvetica", 18)
    c.drawCentredString(width/2, height-200, "This certifies that")

    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width/2, height-260, student_name)

    c.setFont("Helvetica", 18)
    c.drawCentredString(
        width/2,
        height-320,
        "has successfully completed the AI Essentials Program"
    )

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(
        width/2,
        height-370,
        "Chumcred Academy"
    )

    today = datetime.today().strftime("%B %d, %Y")

    c.drawCentredString(width/2, height-420, f"Issued: {today}")

    c.drawCentredString(width/2, height-480, "Dr. Adekunle Adegbie")
    c.drawCentredString(width/2, height-500, "Program Coordinator")

    c.save()

    buffer.seek(0)

    return buffer
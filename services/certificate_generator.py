from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from datetime import datetime
import uuid
import os

TEMPLATE_PATH = "assets/certificates/ai_essentials_certificate_template.pdf"
OUTPUT_DIR = "generated_certificates"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_certificate(
    student_name: str,
    program_name: str = "AI ESSENTIALS — From Zero to Confident AI User",
    issuer: str = "Chumcred Academy",
):
    """
    Generates a personalized completion certificate
    """

    cert_id = f"CCA-{uuid.uuid4().hex[:8].upper()}"
    issue_date = datetime.now().strftime("%d %B %Y")

    file_name = f"{student_name.replace(' ', '_')}_AI_Essentials_Certificate.pdf"
    output_path = os.path.join(OUTPUT_DIR, file_name)

    c = canvas.Canvas(output_path, pagesize=landscape(A4))

    width, height = landscape(A4)

    # ===== STUDENT NAME =====
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width / 2, height / 2 + 40, student_name)

    # ===== PROGRAM NAME =====
    c.setFont("Helvetica", 20)
    c.drawCentredString(width / 2, height / 2 - 10, program_name)

    # ===== ISSUER =====
    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height / 2 - 60, f"Issued by {issuer}")

    # ===== DATE & CERT ID =====
    c.setFont("Helvetica", 12)
    c.drawString(1.2 * inch, 0.8 * inch, f"Issue Date: {issue_date}")
    c.drawRightString(
        width - 1.2 * inch,
        0.8 * inch,
        f"Certificate ID: {cert_id}"
    )

    c.showPage()
    c.save()

    return {
        "certificate_id": cert_id,
        "file_path": output_path,
        "issue_date": issue_date
    }

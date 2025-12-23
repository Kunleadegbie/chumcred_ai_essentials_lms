import shutil
from datetime import datetime


def issue_certificate(user):
    src = "assets/certificates/ai_essentials_certificate_template.pdf"
    dst = f"generated_certificates/certificate_{user['id']}.pdf"

    shutil.copy(src, dst)
    return dst

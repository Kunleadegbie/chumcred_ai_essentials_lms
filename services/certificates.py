import shutil
from datetime import datetime


def issue_certificate(user):
    src = "assets/certificates/ai_essentials_certificate_template.pdf"
    dst = f"generated_certificates/certificate_{user['id']}.pdf"

    shutil.copy(src, dst)
    return dst


# --------------------------------------------------
# CERTIFICATE CHECK
# --------------------------------------------------
def has_certificate(user_id: int) -> bool:
    """
    Returns True if a certificate has already been issued
    for the given user.
    """
    from services.db import read_conn

    with read_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1
            FROM certificates
            WHERE user_id = ?
            LIMIT 1
            """,
            (user_id,),
        )
        return cur.fetchone() is not None


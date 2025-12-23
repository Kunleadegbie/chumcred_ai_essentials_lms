import streamlit as st
from services.certificate_generator import generate_certificate
from services.db import get_conn

def issue_certificate_ui():
    st.header("🎓 Issue Completion Certificate")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.id, u.full_name
        FROM users u
        WHERE u.role = 'student'
    """)
    students = cur.fetchall()

    student = st.selectbox(
        "Select Student",
        students,
        format_func=lambda x: x["full_name"]
    )

    if st.button("Generate Certificate"):
        cert = generate_certificate(student["full_name"])

        cur.execute("""
            INSERT INTO certificates (user_id, certificate_id, file_path, issued_on)
            VALUES (?, ?, ?, ?)
        """, (
            student["id"],
            cert["certificate_id"],
            cert["file_path"],
            cert["issue_date"]
        ))

        conn.commit()
        conn.close()

        st.success("✅ Certificate issued successfully")
        st.download_button(
            "⬇ Download Certificate",
            data=open(cert["file_path"], "rb"),
            file_name=cert["file_path"].split("/")[-1]
        )

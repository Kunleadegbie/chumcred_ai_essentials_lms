import streamlit as st
from utils.db import get_connection

import streamlit as st

def show_admin_unlock():

    st.header("Admin – Unlock Final Exam")

    student_id = st.text_input("Student ID")

    if st.button("Unlock Exam"):
        st.success(f"Exam unlocked for {student_id}")

st.title("Admin: Unlock Week 6 Final Exam")

conn = get_connection()
cursor = conn.cursor()

student_id = st.number_input("Enter Student ID", step=1)

if st.button("Unlock Exam"):

    cursor.execute(
        "UPDATE student_exam_status SET exam_unlocked = 1, exam_reviewed = 0 WHERE user_id=?",
        (student_id,)
    )

    conn.commit()

    st.success("Exam unlocked for student.")
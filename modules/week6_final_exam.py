import streamlit as st
from services.db import read_conn, write_txn
from utils.certificate_generator import generate_certificate


def show_exam(user):

    st.title("Week 6 Final Assessment")

    user_id = user["id"]
    student_name = user["username"]

    # -------------------------------
    # Ensure exam record exists
    # -------------------------------
    with read_conn() as conn:
        row = conn.execute(
            "SELECT * FROM student_exam_status WHERE user_id=?",
            (user_id,)
        ).fetchone()

    if row is None:
        with write_txn() as conn:
            conn.execute(
                """
                INSERT INTO student_exam_status
                (user_id, exam_unlocked, exam_reviewed, attempts, last_score)
                VALUES (?,0,0,0,0)
                """,
                (user_id,)
            )
        st.warning("Final exam not yet unlocked by admin.")
        st.stop()

    if row["exam_unlocked"] == 0:
        st.warning("Final exam not yet unlocked by admin.")
        st.stop()

    if row["exam_reviewed"] == 1:
        st.error("You already reviewed the answers. Exam locked.")
        st.stop()

    # -------------------------------
    # Start exam session
    # -------------------------------
    if "exam_started" not in st.session_state:
        st.session_state.exam_started = False

    if not st.session_state.exam_started:
        if st.button("Start Exam"):
            st.session_state.exam_started = True
            st.rerun()
        st.stop()

    # -------------------------------
    # Questions
    # -------------------------------
    questions = [
        ("What does AI stand for?",
         ["Automated Internet","Artificial Intelligence","Advanced Info","Auto Interface"],
         "Artificial Intelligence"),

        ("Which tool is AI?",
         ["ChatGPT","Notepad","Calculator","Excel"],
         "ChatGPT"),

        ("Prompt engineering means?",
         ["Writing better instructions","Coding hardware","Internet repair","Game design"],
         "Writing better instructions"),

        ("AI helps productivity by?",
         ["Automating tasks","Deleting files","Shutting computers","Blocking internet"],
         "Automating tasks"),

        ("Responsible AI means?",
         ["Using ethically","Sharing private data","Blind trust","Ignoring outputs"],
         "Using ethically"),

        ("AI helps businesses?",
         ["Analyse data","Delete records","Reduce customers","Stop sales"],
         "Analyse data"),

        ("Good prompt is?",
         ["Clear instructions","Confusing text","No question","Random words"],
         "Clear instructions"),

        ("AI supports decisions using?",
         ["Data insights","Guessing","Random output","Deleting data"],
         "Data insights"),

        ("AI tools help professionals?",
         ["Work faster","Stop thinking","Avoid computers","Replace internet"],
         "Work faster"),

        ("Goal of this course?",
         ["Confident AI user","Avoid tech","Stop learning","Ignore AI"],
         "Confident AI user")
    ]

    # -------------------------------
    # Initialize answers
    # -------------------------------
    if "answers" not in st.session_state:
        st.session_state.answers = [None] * len(questions)

    # -------------------------------
    # Display questions
    # -------------------------------
    for i, (q, opts, correct) in enumerate(questions):

        st.session_state.answers[i] = st.radio(
            f"Q{i+1}. {q}",
            opts,
            index=None if st.session_state.answers[i] is None else opts.index(st.session_state.answers[i]),
            key=f"q{i}"
        )

    # -------------------------------
    # Finish Exam
    # -------------------------------
    if st.button("Finish Exam"):

        score = 0

        for i, (q, opts, correct) in enumerate(questions):
            if st.session_state.answers[i] == correct:
                score += 1

        with write_txn() as conn:
            conn.execute(
                """
                UPDATE student_exam_status
                SET last_score=?, attempts=attempts+1
                WHERE user_id=?
                """,
                (score, user_id)
            )

        st.success(f"Your Score: {score}/10")

        if score >= 7:
            st.success("Congratulations! You passed the exam.")

            certificate = generate_certificate(student_name)

            st.download_button(
                "Download Certificate",
                certificate,
                file_name="chumcred_certificate.pdf",
                mime="application/pdf"
            )

    # -------------------------------
    # Review Answers
    # -------------------------------
    if st.button("Review Answers"):

        for i, (q, opts, correct) in enumerate(questions):
            st.write(f"Q{i+1} Correct Answer: {correct}")

        with write_txn() as conn:
            conn.execute(
                "UPDATE student_exam_status SET exam_reviewed=1 WHERE user_id=?",
                (user_id,)
            )
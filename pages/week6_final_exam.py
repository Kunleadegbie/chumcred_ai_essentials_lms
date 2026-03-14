import streamlit as st
from utils.db import get_connection
from utils.certificate_generator import generate_certificate

st.title("Week 6 Final Assessment")

# example student session
user_id = st.session_state.get("user_id")

conn = get_connection()
cursor = conn.cursor()

cursor.execute(
    "SELECT * FROM student_exam_status WHERE user_id=?",
    (user_id,)
)

record = cursor.fetchone()

if not record:

    cursor.execute(
        "INSERT INTO student_exam_status (user_id) VALUES (?)",
        (user_id,)
    )

    conn.commit()

    st.warning("Exam not yet unlocked by admin.")
    st.stop()

if record["exam_unlocked"] == 0:

    st.warning("Final exam will be unlocked after admin approval.")
    st.stop()

if record["exam_reviewed"] == 1:

    st.error("You have already reviewed answers. Exam locked.")
    st.stop()


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


answers = []

for i,(q,opts,correct) in enumerate(questions):

    ans = st.radio(f"Q{i+1}. {q}", opts, key=i)

    answers.append(ans)


if st.button("Finish Exam"):

    score = 0

    for i,(q,opts,correct) in enumerate(questions):

        if answers[i] == correct:
            score += 1

    cursor.execute(
        "UPDATE student_exam_status SET last_score=?, attempts=attempts+1 WHERE user_id=?",
        (score,user_id)
    )

    conn.commit()

    st.success(f"Your Score: {score}/10")

    if score >= 7:

        st.success("Congratulations! You passed the exam.")

        certificate = generate_certificate(st.session_state.get("name"))

        st.download_button(
            label="Download Certificate",
            data=certificate,
            file_name="chumcred_certificate.pdf",
            mime="application/pdf"
        )


if st.button("Review Answers"):

    for i,(q,opts,correct) in enumerate(questions):

        st.write(f"Q{i+1} Correct Answer: {correct}")

    cursor.execute(
        "UPDATE student_exam_status SET exam_reviewed=1 WHERE user_id=?",
        (user_id,)
    )

    conn.commit()
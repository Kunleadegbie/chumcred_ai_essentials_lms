import streamlit as st
from services.db import init_db
from services.auth import login_user
from ui.admin import admin_router
from ui.student import student_router

init_db()

st.set_page_config(
    page_title="Chumcred Academy LMS",
    page_icon="🎓",
    layout="wide"
)


# LOGO
st.sidebar.image("assets/logo.png", width=180)

user = login_user()

if user:
    if user["role"] == "admin":
        admin_router(user)
    else:
        student_router(user)
else:
    st.info("Please log in to continue.")


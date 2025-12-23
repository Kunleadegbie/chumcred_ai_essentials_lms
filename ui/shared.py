import streamlit as st
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, "content")


def load_week_markdown(week_number):
    """
    Loads markdown content for a given week.
    """
    file_path = os.path.join(CONTENT_DIR, f"week{week_number}.md")

    if not os.path.exists(file_path):
        st.error("⚠️ Content file not found for this week.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)

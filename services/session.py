import streamlit as st

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

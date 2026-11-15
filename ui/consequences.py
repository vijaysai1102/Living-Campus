import streamlit as st


def render_consequences() -> None:
    lines = st.session_state.pop("consequence_lines", [])
    if not lines:
        return
    for line in lines:
        st.toast(line)
        st.info(line)

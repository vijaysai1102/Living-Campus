import streamlit as st
from core.clock import is_finals_week
from core.reset import clear_session_campus, start_new_semester
from core.story_engine import ending_tags, format_ending_recap


def render_ending_if_due() -> bool:
    if not is_finals_week():
        return False
    st.markdown("# Finals week 🎓")
    st.markdown("The semester is over. This is what campus remembers.")
    st.divider()
    recap = format_ending_recap()
    st.markdown(recap.replace("\n", "\n\n"))
    tags = ending_tags()
    if tags:
        st.caption("Ending tags: " + ", ".join(tags))
    if st.button("Start a new semester", type="primary", use_container_width=True):
        start_new_semester()
        clear_session_campus(st.session_state)
        st.rerun()
    st.stop()
    return True

import streamlit as st
from core.clock import format_clock, get_clock, skip_day
from core.consequences import format_consequences, snapshot_relationships


def render_campus_clock() -> None:
    clock = get_clock()
    st.markdown(f"### 🕒 {format_clock(clock)}")
    st.caption("Simulated time. Talking and walking both spend a period.")
    if st.button("Skip to next day", use_container_width=True, key="skip_day"):
        before = snapshot_relationships()
        events = skip_day()
        st.session_state.last_gossip = events
        st.session_state.consequence_lines = format_consequences(
            before, snapshot_relationships(), events
        )
        st.rerun()

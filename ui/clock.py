import streamlit as st
from core.clock import advance_period, format_clock, get_clock, skip_day
from core.consequences import format_consequences, snapshot_relationships
from core.digest import while_you_were_away


def render_campus_clock() -> None:
    clock = get_clock()
    st.markdown(f"### 🕒 {format_clock(clock)}")
    st.caption("Simulated time. Talking and walking both spend a period.")
    if st.button("Leave / next period", use_container_width=True, key="leave_period"):
        before = snapshot_relationships()
        events = advance_period()
        st.session_state.last_gossip = events
        st.session_state.consequence_lines = format_consequences(
            before, snapshot_relationships(), events
        )
        st.session_state.active_npc = None
        st.rerun()
    if st.button("Skip to next day", use_container_width=True, key="skip_day"):
        before = snapshot_relationships()
        events = skip_day()
        st.session_state.last_gossip = events
        st.session_state.consequence_lines = format_consequences(
            before, snapshot_relationships(), events
        )
        st.session_state.away_digest = while_you_were_away()
        st.rerun()

import streamlit as st
from core.gossip_engine import player_pulse


def render_campus_pulse() -> None:
    items = player_pulse(limit=5)
    st.markdown("### 📡 Campus Pulse")
    if not items:
        st.caption("Quiet for now. What you say here can still travel later.")
        return
    for item in items:
        st.markdown(
            f'<div style="border-left:2px solid #38bdf8;padding:4px 8px;margin-bottom:6px;'
            f'font-size:0.82rem;color:#e2e8f0">{item}</div>',
            unsafe_allow_html=True,
        )
    st.caption("You hear hallway noise. You do not see private reports.")

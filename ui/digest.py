import streamlit as st
from core.digest import while_you_were_away


def render_away_digest(persistent: bool = False) -> None:
    if persistent:
        lines = while_you_were_away()
    else:
        lines = st.session_state.pop("away_digest", [])
    if not lines:
        return
    body = "\n".join(f"- {line}" for line in lines)
    st.info(f"**While you were away**\n\n{body}")

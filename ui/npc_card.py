import streamlit as st
from core.traits import get_observed_traits


def render_npc_card(npc: dict) -> None:
    st.markdown(f"## {npc['emoji']} {npc['name']}")
    st.caption(npc["role"])
    st.divider()

    st.markdown("**Personality**")
    trait_html = " ".join(
        f'<span style="background:#1e3a5f;color:#7dd3fc;padding:2px 8px;border-radius:12px;font-size:0.75rem">{t}</span>'
        for t in npc.get("traits", [])
    )
    st.markdown(trait_html, unsafe_allow_html=True)

    st.markdown("")
    st.markdown(f"**Goal:** {npc.get('goal', '')}")
    st.markdown(f"**Fear:** {npc.get('fear', '')}")
    render_how_they_see_you(npc.get("id", ""))
    st.divider()


def render_how_they_see_you(npc_id: str) -> None:
    traits = get_observed_traits(npc_id)
    st.markdown("**How they see you**")
    if not traits:
        st.caption("No impression yet. What you do here sticks.")
        return
    chips = " ".join(
        f'<span style="background:#3f1d2e;color:#fda4af;padding:2px 8px;border-radius:12px;font-size:0.75rem">{t}</span>'
        for t in traits
    )
    st.markdown(chips, unsafe_allow_html=True)

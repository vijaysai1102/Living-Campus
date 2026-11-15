import streamlit as st
from core.clock import format_clock, get_clock
from core.consequences import format_consequences, snapshot_relationships
from core.gossip_engine import advance_and_resolve
from core.npc_loader import load_npc
from core.schedules import current_slot, locations, npcs_at


def _go_talk(npc_id: str) -> None:
    if st.session_state.active_npc not in (None, npc_id):
        before = snapshot_relationships()
        events = advance_and_resolve()
        st.session_state.last_gossip = events
        st.session_state.consequence_lines = format_consequences(
            before, snapshot_relationships(), events
        )
    st.session_state.active_npc = npc_id
    st.rerun()


def render_campus_map(primary: bool = True) -> None:
    clock = get_clock()
    title = "Campus map" if primary else "Where is everyone?"
    st.markdown(f"### 🗺️ {title}")
    st.caption(f"Right now: {format_clock(clock)}")

    place_cols = st.columns(3)
    for index, location in enumerate(locations()):
        here = npcs_at(location, clock)
        selected = st.session_state.get("selected_location") == location
        label = f"{location}"
        if here:
            label += f" · {len(here)}"
        with place_cols[index % 3]:
            if st.button(
                label,
                key=f"map_loc_{location}_{primary}",
                use_container_width=True,
                type="primary" if selected else "secondary",
            ):
                st.session_state.selected_location = location
                st.rerun()

    selected = st.session_state.get("selected_location")
    if not selected:
        st.caption("Pick a place to see who is there.")
        return

    here = npcs_at(selected, clock)
    st.markdown(f"**At {selected}**")
    if not here:
        st.caption("Empty right now. Time skip or try another building.")
        return
    for npc_id in here:
        npc = load_npc(npc_id)
        slot = current_slot(npc_id, clock) or {}
        status = "free to talk" if slot.get("interruptible") else "busy — hallway wave only"
        if st.button(
            f"{npc['emoji']} Talk to {npc['name']}  \n{status}",
            key=f"map_talk_{npc_id}_{primary}",
            use_container_width=True,
        ):
            _go_talk(npc_id)

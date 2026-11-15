"""Honest reset of NPC / campus simulation state."""

from core.emotion_engine import reset_emotions
from core.memory_manager import clear_chat_history, clear_memories
from core.npc_loader import load_all_npcs, load_npc
from core.relationship_engine import reset_relationship
from core.gossip_engine import clear_gossip_state
from core.social_graph import clear_facts, clear_knowledge, reset_opinions
from core.traits import clear_observed_traits
from core.promises import clear_promises
from core.clock import reset_clock


def reset_npc(npc_id: str) -> None:
    """Wipe one NPC's persisted state back to first-meeting defaults."""
    npc = load_npc(npc_id)
    reset_emotions(npc_id, npc["initial_mood"])
    reset_relationship(npc_id)
    clear_memories(npc_id)
    clear_chat_history(npc_id)
    clear_knowledge(npc_id)
    reset_opinions(npc_id)
    clear_gossip_state(npc_id)
    clear_observed_traits(npc_id)
    clear_promises(npc_id)


def reset_campus() -> None:
    """Wipe every NPC so a new semester can start clean."""
    for npc in load_all_npcs():
        reset_npc(npc["id"])
    clear_facts()
    reset_opinions()
    clear_gossip_state()
    reset_clock()


def clear_session_npc(session_state, npc_id: str) -> None:
    """Drop Streamlit session leftovers so the next visit regenerates an opening."""
    histories = session_state.get("chat_histories")
    if isinstance(histories, dict):
        histories.pop(npc_id, None)
    opening_sent = session_state.get("opening_sent")
    if isinstance(opening_sent, set):
        opening_sent.discard(npc_id)


def clear_session_campus(session_state) -> None:
    session_state["chat_histories"] = {}
    session_state["opening_sent"] = set()
    session_state["active_npc"] = None
    session_state["last_gossip"] = []
    session_state["consequence_lines"] = []
    session_state["selected_location"] = None

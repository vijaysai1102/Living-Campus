from core.npc_loader import load_npc
from core.emotion_engine import get_emotions, mood_for_prompt
from core.relationship_engine import get_relationship
from core.memory_manager import get_relevant_memories
from core.rag_retriever import retrieve_context
from core.gossip_engine import format_heard_around_campus
from core.social_graph import format_opinions_for_prompt
from core.player import format_player_for_prompt
from core.traits import format_observed_traits
from core.clock import format_clock_for_prompt
from core.schedules import format_location_for_prompt
from ai.gemini_client import generate_response
from ai.prompt_builder import build_opening_prompt
from config.settings import MEMORY_CONTEXT_COUNT, RAG_TOP_K


def generate_opening(npc_id: str) -> str:
    npc = load_npc(npc_id)
    emotions = mood_for_prompt(npc_id, get_emotions(npc_id))
    relationship = get_relationship(npc_id)
    memories = get_relevant_memories(npc_id, query="", n=MEMORY_CONTEXT_COUNT)
    rag_context = retrieve_context(npc_id, query="", top_k=RAG_TOP_K)
    gossip_text = format_heard_around_campus(npc_id)
    opinions_text = format_opinions_for_prompt(npc_id)

    prompt = build_opening_prompt(
        npc,
        emotions,
        relationship,
        memories,
        rag_context,
        gossip_text=gossip_text,
        opinions_text=opinions_text,
        player_text=format_player_for_prompt(),
        traits_text=format_observed_traits(npc_id),
        clock_text=format_clock_for_prompt(),
        location_text=format_location_for_prompt(npc_id),
    )
    result = generate_response(prompt)
    return result.get("reply", f"Hey. What do you want?")

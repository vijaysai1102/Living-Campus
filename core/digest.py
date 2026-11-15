"""A short, non-LLM digest of time, rumors, and deadlines."""

from core.clock import format_clock, get_clock
from core.gossip_engine import player_pulse
from core.rag_retriever import retrieve_context


def while_you_were_away(limit: int = 4) -> list[str]:
    clock = get_clock()
    lines = [f"Campus time: {format_clock(clock)}."]
    for item in player_pulse(limit=2):
        if item not in lines:
            lines.append(item)

    seen_titles = set()
    week = int(clock.get("week") or 6)
    for npc_id in ("professor", "ta", "friend"):
        for item in retrieve_context(npc_id, query="deadline midterm exam assignment", clock=clock, top_k=4):
            title = item.get("title") or ""
            due = item.get("due_week")
            if not title or title in seen_titles:
                continue
            if due in {week, week + 1}:
                seen_titles.add(title)
                lines.append(f"Coming up: {title} (week {due}).")
            if len(lines) >= limit:
                return lines[:limit]
    return lines[:limit]

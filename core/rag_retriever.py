import json
from pathlib import Path
from config.settings import CAMPUS_CONTEXT_DIR, RAG_TOP_K

_CONTEXT_FILES = ["events.json", "assignments.json", "rumors.json", "announcements.json", "lore.json"]
_LIST_KEYS = ["events", "assignments", "rumors", "announcements", "lore"]


def _load_all_context() -> list[dict]:
    items = []
    for fname, list_key in zip(_CONTEXT_FILES, _LIST_KEYS):
        path = CAMPUS_CONTEXT_DIR / fname
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items.extend(data.get(list_key, []))
    return items


def _current_week(clock: dict | None = None) -> int:
    if clock and clock.get("week") is not None:
        return int(clock["week"])
    try:
        from core.clock import get_clock
        return int(get_clock()["week"])
    except Exception:
        return 6


def _due_week(item: dict) -> int | None:
    raw = item.get("due_week", item.get("week"))
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def retrieve_context(npc_id: str, query: str = "", top_k: int = RAG_TOP_K, clock: dict | None = None) -> list[dict]:
    all_items = _load_all_context()
    relevant = [item for item in all_items if npc_id in item.get("npc_relevance", [])]
    current_week = _current_week(clock)

    live = []
    for item in relevant:
        due = _due_week(item)
        if due is not None and due < current_week:
            continue
        live.append(item)

    if not live:
        return []

    query_words = set(query.lower().split()) if query else set()

    def score(item: dict) -> int:
        text = " ".join([
            item.get("title", ""),
            item.get("content", ""),
            item.get("description", "")
        ]).lower()
        keyword_score = sum(1 for w in query_words if len(w) > 3 and w in text)
        tag_text = " ".join(item.get("tags", []))
        tag_score = sum(1 for w in query_words if w in tag_text) * 2
        due = _due_week(item)
        boost = 5 if due in {current_week, current_week + 1} else 0
        return keyword_score + tag_score + boost

    scored = sorted(live, key=score, reverse=True)
    return scored[:top_k]


def format_context(items: list[dict]) -> str:
    if not items:
        return "No specific campus context available right now."
    lines = []
    for item in items:
        title = item.get("title") or item.get("id", "")
        body = item.get("content") or item.get("description", "")
        lines.append(f"• [{title}] {body}")
    return "\n".join(lines)

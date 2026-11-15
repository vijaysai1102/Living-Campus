"""Turn model output into campus facts the speaker already knows."""

from core.social_graph import create_fact, grant_knowledge


def ingest_shareable_facts(npc_id: str, result: dict) -> list[int]:
    texts = [t.strip() for t in result.get("shareable_facts") or [] if str(t).strip()]
    if not texts:
        return []

    keep_secret = bool(result.get("keep_secret", False))
    try:
        sensitivity = int(result.get("fact_sensitivity", 40))
    except (TypeError, ValueError):
        sensitivity = 40
    if keep_secret:
        sensitivity = max(sensitivity, 70)

    fact_ids = []
    for text in texts[:2]:
        fact_id = create_fact(
            fact_text=text,
            source_npc_id=npc_id,
            about_player=True,
            sensitivity=sensitivity,
            keep_secret=keep_secret,
        )
        grant_knowledge(npc_id, fact_id, status="known", hop=0)
        fact_ids.append(fact_id)
    return fact_ids

"""Turn model output into campus facts the speaker already knows."""

from core.relationship_engine import get_relationship
from core.social_graph import adjust_opinion, create_fact, grant_knowledge, mentioned_npc_id


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
        about_npc_id = mentioned_npc_id(text, speaker_id=npc_id)
        fact_id = create_fact(
            fact_text=text,
            source_npc_id=npc_id,
            about_player=True,
            about_npc_id=about_npc_id,
            sensitivity=sensitivity,
            keep_secret=keep_secret,
        )
        grant_knowledge(npc_id, fact_id, status="known", hop=0)
        if about_npc_id:
            friendship = get_relationship(npc_id).get("friendship", 30)
            side = 1 if friendship >= 40 else 0
            adjust_opinion(
                npc_id,
                about_npc_id,
                irritation=4 + side,
                respect=-2,
            )
        fact_ids.append(fact_id)
    return fact_ids

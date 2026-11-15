"""Rule-based rumor mill. Simulates who would tell whom — no extra LLM calls."""

from core.npc_loader import load_all_npcs
from core.relationship_engine import get_relationship
from core.social_graph import (
    get_knowledge_for_npc,
    get_opinion,
    grant_knowledge,
    list_recent_facts,
)

GOSSIP_TRAITS = {
    "friend": {"max_sensitivity": 85, "keeps_secrets_at_trust": 70},
    "ta": {"max_sensitivity": 58, "keeps_secrets_at_trust": 50},
    "professor": {"max_sensitivity": 35, "keeps_secrets_at_trust": 40},
}

ACADEMIC_INTEGRITY_MARKERS = (
    "chatgpt", "ai-generated", "plagiar", "moss", "cheat", "leaked guide", "study guide",
)

AUTHORITY_NPC = "professor"


def npc_ids() -> list[str]:
    return [npc["id"] for npc in load_all_npcs()]


def heard_text(item: dict) -> str:
    if int(item.get("hop") or 0) >= 2 and item.get("distorted_text"):
        return item["distorted_text"]
    return item.get("fact_text") or ""


def format_heard_around_campus(npc_id: str, limit: int = 8) -> str:
    items = get_knowledge_for_npc(npc_id)[:limit]
    if not items:
        return "You have not heard any campus gossip about this student recently."
    lines = []
    for item in items:
        hop = int(item.get("hop") or 0)
        if hop == 0 and item.get("source_npc_id") == npc_id:
            how = "the student told you this"
        elif hop == 0:
            how = "you know this directly"
        else:
            how = "you heard this as a rumor"
        lines.append(f"- ({how}) {heard_text(item)}")
    return "\n".join(lines)


def distort_text(fact_text: str, hop: int) -> str:
    text = fact_text.strip()
    if hop < 2:
        return text
    lowered = text[0].lower() + text[1:] if text else text
    return f"Someone in CS mentioned that {lowered}"


def will_share(source_id: str, listener_id: str, fact: dict) -> bool:
    if source_id == listener_id:
        return False

    traits = GOSSIP_TRAITS.get(source_id, {"max_sensitivity": 40, "keeps_secrets_at_trust": 60})
    sensitivity = int(fact.get("sensitivity") or 0)
    keep_secret = bool(fact.get("keep_secret"))
    player_trust = get_relationship(source_id).get("trust", 50)
    opinion = get_opinion(source_id, listener_id) or {"trust": 40, "respect": 40, "irritation": 20}

    if keep_secret and player_trust >= traits["keeps_secrets_at_trust"]:
        return False

    academic = _is_academic_integrity(fact.get("fact_text", ""))

    # Webb almost never gossips, and never to Batman.
    if source_id == "professor":
        if listener_id == "friend":
            return False
        return academic and sensitivity >= 70 and not keep_secret

    # Students do not walk into Webb's office to spill gossip.
    if listener_id == AUTHORITY_NPC and source_id != "ta":
        return False

    # Kevin reports academic integrity issues to Webb unless he promised secrecy.
    if source_id == "ta" and listener_id == AUTHORITY_NPC:
        return academic and not keep_secret and player_trust < 70

    if sensitivity > traits["max_sensitivity"] and not (source_id == "friend" and not keep_secret):
        return False

    if keep_secret and source_id != "friend":
        return False

    # Batman leaks more readily, especially to Kevin.
    if source_id == "friend":
        if keep_secret and player_trust >= 70:
            return False
        if listener_id == "ta":
            return sensitivity <= 90
        return sensitivity <= 70 and opinion.get("trust", 0) >= 20

    # Kevin vents to Batman about non-secret, medium-sensitivity stuff.
    if source_id == "ta" and listener_id == "friend":
        return not keep_secret and sensitivity <= traits["max_sensitivity"] and opinion.get("trust", 0) >= 30

    return not keep_secret and sensitivity <= traits["max_sensitivity"]


def propagate_facts(source_npc_id: str | None = None) -> list[dict]:
    """Spread currently known facts to anyone who should hear them now."""
    facts = list_recent_facts(limit=100)
    if source_npc_id:
        facts = [f for f in facts if f.get("source_npc_id") == source_npc_id or _npc_knows(source_npc_id, f["id"])]

    spread = []
    for fact in facts:
        holders = _holders(fact["id"])
        if not holders:
            continue
        for source_id, hop in holders:
            for listener_id in npc_ids():
                if listener_id in {h[0] for h in holders}:
                    continue
                if not will_share(source_id, listener_id, fact):
                    continue
                new_hop = hop + 1
                status = "rumor" if new_hop >= 1 else "known"
                grant_knowledge(listener_id, fact["id"], status=status, hop=new_hop)
                if new_hop >= 2 and not fact.get("distorted_text"):
                    _store_distortion(fact["id"], distort_text(fact["fact_text"], new_hop))
                event = {
                    "fact_id": fact["id"],
                    "from": source_id,
                    "to": listener_id,
                    "hop": new_hop,
                    "status": status,
                }
                spread.append(event)
                holders.append((listener_id, new_hop))
    return spread


def _holders(fact_id: int) -> list[tuple[str, int]]:
    holders = []
    for npc_id in npc_ids():
        for item in get_knowledge_for_npc(npc_id):
            if item["fact_id"] == fact_id and item["status"] != "denied":
                holders.append((npc_id, int(item.get("hop") or 0)))
    return holders


def _npc_knows(npc_id: str, fact_id: int) -> bool:
    return any(item["fact_id"] == fact_id for item in get_knowledge_for_npc(npc_id))


def _is_academic_integrity(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ACADEMIC_INTEGRITY_MARKERS)


def _store_distortion(fact_id: int, text: str) -> None:
    from core.database import get_connection

    conn = get_connection()
    conn.execute(
        "UPDATE campus_facts SET distorted_text = ? WHERE id = ? AND (distorted_text IS NULL OR distorted_text = '')",
        (text, fact_id),
    )
    conn.commit()
    conn.close()

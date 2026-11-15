"""Rule-based rumor mill. Simulates who would tell whom — no extra LLM calls."""

from core.npc_loader import load_all_npcs
from core.relationship_engine import get_relationship, update_relationship
from core.social_graph import (
    adjust_opinion,
    get_fact,
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


def _npc_name(npc_id: str) -> str:
    for npc in load_all_npcs():
        if npc["id"] == npc_id:
            return npc["name"]
    return npc_id


def player_pulse(limit: int = 5) -> list[str]:
    """What the student can reasonably know is in the air — not who reported whom."""
    lines = []
    seen = set()
    for fact in list_recent_facts(limit=20):
        text = (fact.get("fact_text") or "").strip()
        if not text or text in seen:
            continue
        source_id = fact.get("source_npc_id")
        holders = _holders(fact["id"])
        hops = [hop for _, hop in holders]
        leaked = any(hop >= 1 for hop in hops)
        if source_id:
            lines.append(f"You told {_npc_name(source_id)}: {text}")
        if leaked:
            rumor = fact.get("distorted_text") or "People in CS are repeating a version of that story."
            if rumor == text:
                rumor = "A hallway rumor is going around about that."
            lines.append(rumor)
        seen.add(text)
        if len(lines) >= limit:
            break
    return lines[:limit]


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


def delay_for(source_id: str, listener_id: str, hop: int) -> int:
    # Kevin reporting to Webb is slower than hallway gossip.
    if source_id == "ta" and listener_id == AUTHORITY_NPC:
        return 2
    return 1


def get_tick() -> int:
    from core.database import get_connection

    conn = get_connection()
    row = conn.execute("SELECT tick FROM campus_state WHERE id = 1").fetchone()
    if row is None:
        conn.execute("INSERT OR IGNORE INTO campus_state (id, tick) VALUES (1, 0)")
        conn.commit()
        conn.close()
        return 0
    conn.close()
    return int(row["tick"])


def advance_tick(n: int = 1) -> int:
    from core.database import get_connection

    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO campus_state (id, tick) VALUES (1, 0)")
    conn.execute("UPDATE campus_state SET tick = tick + ? WHERE id = 1", (n,))
    conn.commit()
    tick = conn.execute("SELECT tick FROM campus_state WHERE id = 1").fetchone()["tick"]
    conn.close()
    return int(tick)


def collect_spreads() -> list[dict]:
    """One hop of would-share events that are not already known or queued."""
    spreads = []
    for fact in list_recent_facts(limit=100):
        known = {holder[0] for holder in _holders(fact["id"])}
        pending_to = _pending_listeners(fact["id"])
        blocked = known | pending_to
        for source_id, hop in _holders(fact["id"]):
            for listener_id in npc_ids():
                if listener_id in blocked:
                    continue
                if not will_share(source_id, listener_id, fact):
                    continue
                new_hop = hop + 1
                event = {
                    "fact_id": fact["id"],
                    "from": source_id,
                    "to": listener_id,
                    "hop": new_hop,
                    "status": "rumor" if new_hop >= 1 else "known",
                    "fact_text": fact.get("fact_text", ""),
                }
                spreads.append(event)
                blocked.add(listener_id)
    return spreads


def queue_new_gossip() -> list[dict]:
    from core.database import get_connection

    tick = get_tick()
    queued = []
    conn = get_connection()
    for event in collect_spreads():
        due = tick + delay_for(event["from"], event["to"], event["hop"])
        conn.execute(
            """
            INSERT OR IGNORE INTO pending_gossip
                (fact_id, from_npc_id, to_npc_id, hop, status, due_tick)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event["fact_id"], event["from"], event["to"], event["hop"], event["status"], due),
        )
        queued.append({**event, "due_tick": due})
    conn.commit()
    conn.close()
    return queued


def resolve_due_gossip() -> list[dict]:
    from core.database import get_connection

    tick = get_tick()
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM pending_gossip WHERE due_tick <= ? ORDER BY due_tick, id",
        (tick,),
    ).fetchall()
    delivered = []
    for row in rows:
        event = dict(row)
        grant_knowledge(event["to_npc_id"], event["fact_id"], status=event["status"], hop=event["hop"])
        _apply_heard_about_self(event["to_npc_id"], event["fact_id"], event["from_npc_id"])
        if event["hop"] >= 2:
            from core.social_graph import get_fact
            fact = get_fact(event["fact_id"])
            if fact and not fact.get("distorted_text"):
                _store_distortion(event["fact_id"], distort_text(fact["fact_text"], event["hop"]))
        conn.execute(
            """
            INSERT INTO gossip_log (fact_id, from_npc_id, to_npc_id, hop, tick)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event["fact_id"], event["from_npc_id"], event["to_npc_id"], event["hop"], tick),
        )
        conn.execute("DELETE FROM pending_gossip WHERE id = ?", (event["id"],))
        delivered.append({
            "fact_id": event["fact_id"],
            "from": event["from_npc_id"],
            "to": event["to_npc_id"],
            "hop": event["hop"],
            "status": event["status"],
            "tick": tick,
        })
    conn.commit()
    conn.close()
    return delivered


def advance_and_resolve() -> list[dict]:
    """Campus time passes: due rumors land, then new leaks get scheduled."""
    advance_tick(1)
    delivered = resolve_due_gossip()
    queue_new_gossip()
    return delivered


def recent_gossip_log(limit: int = 8) -> list[dict]:
    from core.database import get_connection

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT g.*, f.fact_text, f.distorted_text, f.sensitivity
        FROM gossip_log g
        JOIN campus_facts f ON f.id = g.fact_id
        ORDER BY g.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_gossip_state(npc_id: str | None = None) -> None:
    from core.database import get_connection

    conn = get_connection()
    if npc_id:
        conn.execute(
            "DELETE FROM pending_gossip WHERE from_npc_id = ? OR to_npc_id = ?",
            (npc_id, npc_id),
        )
    else:
        conn.execute("DELETE FROM pending_gossip")
        conn.execute("DELETE FROM gossip_log")
        conn.execute("INSERT OR IGNORE INTO campus_state (id, tick) VALUES (1, 0)")
        conn.execute("UPDATE campus_state SET tick = 0 WHERE id = 1")
    conn.commit()
    conn.close()


def propagate_facts(source_npc_id: str | None = None) -> list[dict]:
    """Immediate spread helper for tests and debug. Production uses delayed ticks."""
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
                _apply_heard_about_self(listener_id, fact["id"], source_id)
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


def _apply_heard_about_self(listener_id: str, fact_id: int, from_npc_id: str) -> None:
    fact = get_fact(fact_id)
    if not fact or fact.get("about_npc_id") != listener_id:
        return
    update_relationship(listener_id, {"trust": -6, "hostility": 5, "friendship": -4})
    if from_npc_id:
        adjust_opinion(listener_id, from_npc_id, trust=-5, irritation=8)


def _holders(fact_id: int) -> list[tuple[str, int]]:
    holders = []
    for npc_id in npc_ids():
        for item in get_knowledge_for_npc(npc_id):
            if item["fact_id"] == fact_id and item["status"] != "denied":
                holders.append((npc_id, int(item.get("hop") or 0)))
    return holders


def _npc_knows(npc_id: str, fact_id: int) -> bool:
    return any(item["fact_id"] == fact_id for item in get_knowledge_for_npc(npc_id))


def _pending_listeners(fact_id: int) -> set[str]:
    from core.database import get_connection

    conn = get_connection()
    rows = conn.execute(
        "SELECT to_npc_id FROM pending_gossip WHERE fact_id = ?",
        (fact_id,),
    ).fetchall()
    conn.close()
    return {row["to_npc_id"] for row in rows}


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

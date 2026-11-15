"""Per-NPC impressions of the student. Webb and Batman can disagree."""

from core.database import get_connection

MAX_TRAIT_LEN = 32


def _normalize_trait(trait: str) -> str:
    text = (trait or "").strip().lower()
    if not text:
        return ""
    # One adjective: take the first token, drop punctuation.
    token = "".join(ch for ch in text.split()[0] if ch.isalpha() or ch == "-")
    return token[:MAX_TRAIT_LEN]


def observe_trait(npc_id: str, trait: str) -> str | None:
    """Persist a new observed adjective for this NPC. Returns the stored trait or None."""
    normalized = _normalize_trait(trait)
    if not normalized or not npc_id:
        return None
    conn = get_connection()
    conn.execute(
        """
        INSERT OR IGNORE INTO player_traits_observed (npc_id, trait)
        VALUES (?, ?)
        """,
        (npc_id, normalized),
    )
    conn.commit()
    conn.close()
    return normalized


def get_observed_traits(npc_id: str) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT trait FROM player_traits_observed
        WHERE npc_id = ?
        ORDER BY created_at ASC, trait ASC
        """,
        (npc_id,),
    ).fetchall()
    conn.close()
    return [row["trait"] for row in rows]


def format_observed_traits(npc_id: str, traits: list[str] | None = None) -> str:
    traits = traits if traits is not None else get_observed_traits(npc_id)
    if not traits:
        return "You have not yet formed a distinct impression of this student."
    return "How you currently see this student: " + ", ".join(traits)


def clear_observed_traits(npc_id: str | None = None) -> None:
    conn = get_connection()
    if npc_id:
        conn.execute("DELETE FROM player_traits_observed WHERE npc_id = ?", (npc_id,))
    else:
        conn.execute("DELETE FROM player_traits_observed")
    conn.commit()
    conn.close()

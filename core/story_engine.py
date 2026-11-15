"""Flags, authored secrets, and later hooks. JSON is canon; the LLM performs."""

import json
from functools import lru_cache

from config.settings import SECRETS_PATH
from core.database import get_connection
from core.memory_manager import save_memory
from core.relationship_engine import get_relationship, update_relationship

SECRET_STATES = ("unknown", "suspected", "known", "leaked")
_STATE_RANK = {name: index for index, name in enumerate(SECRET_STATES)}


@lru_cache(maxsize=1)
def load_secrets() -> list[dict]:
    if not SECRETS_PATH.exists():
        return []
    with open(SECRETS_PATH, "r", encoding="utf-8") as f:
        return list(json.load(f).get("secrets", []))


def get_flag(key: str, default: str = "") -> str:
    conn = get_connection()
    row = conn.execute("SELECT value FROM flags WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_flag(key: str, value: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO flags (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


def all_flags() -> dict[str, str]:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM flags ORDER BY key").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


def clear_flags() -> None:
    conn = get_connection()
    conn.execute("DELETE FROM flags")
    conn.commit()
    conn.close()


def secret_state(secret_id: str) -> str:
    secret = _secret_by_id(secret_id)
    if not secret:
        return "unknown"
    value = get_flag(secret["flag"], "unknown")
    return value if value in SECRET_STATES else "unknown"


def known_secrets() -> list[dict]:
    found = []
    for secret in load_secrets():
        state = secret_state(secret["id"])
        if state in {"known", "leaked"}:
            found.append({**secret, "state": state})
    return found


def set_secret_state(secret_id: str, state: str) -> str:
    secret = _secret_by_id(secret_id)
    if not secret or state not in SECRET_STATES:
        return "unknown"
    current = secret_state(secret_id)
    if _STATE_RANK[state] <= _STATE_RANK.get(current, 0):
        return current
    set_flag(secret["flag"], state)
    if state == "known":
        save_memory(
            secret["holder"],
            secret.get("summary") or secret.get("title"),
            importance=9,
            tags=secret_id,
            kind="secret",
        )
    if state == "leaked":
        _apply_leak(secret)
    return state


def consider_discovery(npc_id: str, result: dict | None = None) -> list[str]:
    """Advance secret states from this conversation. Player-learnable without reading JSON."""
    from core.clock import get_clock

    result = result or {}
    rel = get_relationship(npc_id)
    clock = get_clock()
    haystack = " ".join([
        str(result.get("memory_note") or ""),
        str(result.get("reply") or ""),
        str(result.get("observed_trait") or ""),
        " ".join(result.get("shareable_facts") or []),
    ]).lower()
    changed = []
    for secret in load_secrets():
        if secret.get("holder") != npc_id:
            continue
        cond = secret.get("discovery_conditions") or {}
        if int(clock.get("week") or 0) < int(cond.get("week_min") or 0):
            continue
        keywords = [k.lower() for k in cond.get("keywords") or []]
        hit = any(keyword in haystack for keyword in keywords)
        trust = int(rel.get("trust") or 0)
        keep_secret = bool(result.get("keep_secret"))
        if hit and not keep_secret and any(keyword in " ".join(result.get("shareable_facts") or []).lower() for keyword in keywords):
            new_state = set_secret_state(secret["id"], "leaked")
        elif hit or trust >= int(cond.get("min_trust_known") or 70):
            new_state = set_secret_state(secret["id"], "known")
        elif trust >= int(cond.get("min_trust") or 60):
            new_state = set_secret_state(secret["id"], "suspected")
        elif trust >= int(cond.get("min_trust_suspected") or 45):
            new_state = set_secret_state(secret["id"], "suspected")
        else:
            continue
        changed.append(f"{secret['id']}:{new_state}")
    return changed


def _secret_by_id(secret_id: str) -> dict | None:
    for secret in load_secrets():
        if secret.get("id") == secret_id:
            return secret
    return None


def _apply_leak(secret: dict) -> None:
    from core.social_graph import create_fact, grant_knowledge

    consequences = secret.get("leak_consequences") or {}
    for npc_id, deltas in (consequences.get("relationship") or {}).items():
        update_relationship(npc_id, deltas)
    fact_text = secret.get("campus_fact") or secret.get("summary")
    if fact_text:
        fact_id = create_fact(
            fact_text=fact_text,
            source_npc_id=secret.get("holder"),
            about_player=True,
            sensitivity=85,
            keep_secret=False,
        )
        if secret.get("holder"):
            grant_knowledge(secret["holder"], fact_id, status="known", hop=0)
    save_memory(
        secret.get("holder") or "friend",
        f"Leaked: {secret.get('title')}",
        importance=9,
        tags=f"{secret.get('id')},leaked",
        kind="secret",
    )

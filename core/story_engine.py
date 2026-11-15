"""Flags, authored secrets, and later hooks. JSON is canon; the LLM performs."""

import json
from functools import lru_cache

from config.settings import FAVORS_PATH, SECRETS_PATH
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


FAVOR_STATES = ("locked", "available", "asked", "succeeded", "failed")


@lru_cache(maxsize=1)
def load_favors() -> list[dict]:
    if not FAVORS_PATH.exists():
        return []
    with open(FAVORS_PATH, "r", encoding="utf-8") as f:
        return list(json.load(f).get("favors", []))


def get_favor_status(favor_id: str) -> str:
    conn = get_connection()
    row = conn.execute("SELECT status FROM favor_status WHERE favor_id = ?", (favor_id,)).fetchone()
    conn.close()
    return row["status"] if row else "locked"


def set_favor_status(favor_id: str, status: str, asked_tick: int | None = None) -> None:
    from core.gossip_engine import get_tick

    tick = asked_tick if asked_tick is not None else get_tick()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO favor_status (favor_id, status, asked_tick)
        VALUES (?, ?, ?)
        ON CONFLICT(favor_id) DO UPDATE SET
            status = excluded.status,
            asked_tick = COALESCE(excluded.asked_tick, favor_status.asked_tick),
            updated_at = CURRENT_TIMESTAMP
        """,
        (favor_id, status, tick),
    )
    conn.commit()
    conn.close()


def clear_favors() -> None:
    conn = get_connection()
    conn.execute("DELETE FROM favor_status")
    conn.commit()
    conn.close()


def open_favors() -> list[dict]:
    open_items = []
    for favor in load_favors():
        status = get_favor_status(favor["id"])
        if status in {"available", "asked"}:
            open_items.append({**favor, "status": status})
    return open_items


def _favor_conditions_met(favor: dict, npc_id: str) -> bool:
    from core.clock import get_clock

    if favor.get("requested_by") != npc_id:
        return False
    cond = favor.get("conditions") or {}
    rel = get_relationship(npc_id)
    clock = get_clock()
    if int(rel.get("trust") or 0) < int(cond.get("trust_min") or 0):
        return False
    if int(rel.get("respect") or 0) < int(cond.get("respect_min") or 0):
        return False
    if int(clock.get("week") or 0) < int(cond.get("week_min") or 0):
        return False
    if cond.get("weekday") and cond["weekday"] != clock.get("weekday"):
        return False
    secret_id = cond.get("secret")
    if secret_id:
        needed = cond.get("secret_min") or "known"
        if _STATE_RANK.get(secret_state(secret_id), 0) < _STATE_RANK.get(needed, 0):
            return False
    return True


def unlock_and_ask_favors(npc_id: str) -> list[dict]:
    """Mark matching favors asked at most once, then return those this NPC should voice."""
    voiced = []
    for favor in load_favors():
        if favor.get("requested_by") != npc_id:
            continue
        status = get_favor_status(favor["id"])
        if status in {"succeeded", "failed"}:
            continue
        if status == "asked":
            voiced.append({**favor, "status": status})
            continue
        if _favor_conditions_met(favor, npc_id):
            set_favor_status(favor["id"], "asked")
            voiced.append({**favor, "status": "asked"})
    return voiced


def format_secret_hooks(npc_id: str) -> str:
    from core.clock import get_clock

    rel = get_relationship(npc_id)
    clock = get_clock()
    lines = []
    for secret in load_secrets():
        if secret.get("holder") != npc_id:
            continue
        cond = secret.get("discovery_conditions") or {}
        if int(clock.get("week") or 0) < int(cond.get("week_min") or 0):
            continue
        if int(rel.get("trust") or 0) < int(cond.get("min_trust") or 0):
            continue
        hook = (secret.get("prompt_hook") or "").strip()
        if not hook:
            continue
        lines.append(f"- {hook} (state: {secret_state(secret['id'])})")
    if not lines:
        return ""
    return "=== SECRET HOOK (authored; do not invent a new quest) ===\n" + "\n".join(lines)


def format_story_hooks(npc_id: str) -> str:
    parts = [format_favor_hooks(npc_id), format_secret_hooks(npc_id)]
    parts = [part for part in parts if part]
    if not parts:
        return "No authored hook this turn. Do not invent a new quest."
    return "\n\n".join(parts)


def format_favor_hooks(npc_id: str) -> str:
    voiced = unlock_and_ask_favors(npc_id)
    if not voiced:
        return ""
    lines = ["=== FAVOR HOOK (authored; do not invent a new quest) ==="]
    for favor in voiced:
        lines.append(f"- {favor['title']}: {favor['ask']}")
        lines.append('  If they agree, set favor_update to "succeeded". If they refuse, set "failed".')
    return "\n".join(lines)


def resolve_favors(npc_id: str, result: dict | None = None) -> list[str]:
    result = result or {}
    haystack = " ".join([
        str(result.get("memory_note") or ""),
        str(result.get("reply") or ""),
        " ".join(result.get("shareable_facts") or []),
        str(result.get("user_message") or ""),
    ]).lower()
    explicit = str(result.get("favor_update") or "").strip().lower()
    changed = []
    for favor in load_favors():
        if favor.get("requested_by") != npc_id:
            continue
        if get_favor_status(favor["id"]) != "asked":
            continue
        outcome = ""
        if explicit in {"succeeded", "failed"}:
            outcome = explicit
        elif any(keyword in haystack for keyword in favor.get("fail_keywords") or []):
            outcome = "failed"
        elif any(keyword in haystack for keyword in favor.get("success_keywords") or []):
            outcome = "succeeded"
        if not outcome:
            continue
        _apply_favor_outcome(favor, outcome)
        changed.append(f"{favor['id']}:{outcome}")
    return changed


def _apply_favor_outcome(favor: dict, outcome: str) -> None:
    payload = favor.get("success") if outcome == "succeeded" else favor.get("fail")
    payload = payload or {}
    set_favor_status(favor["id"], outcome)
    if payload.get("flag"):
        set_flag(payload["flag"], outcome)
    for npc_id, deltas in (payload.get("relationship") or {}).items():
        update_relationship(npc_id, deltas)
    save_memory(
        favor["requested_by"],
        f"Favor {outcome}: {favor.get('title')}",
        importance=8,
        tags=f"favor,{outcome}",
        kind="favor",
    )

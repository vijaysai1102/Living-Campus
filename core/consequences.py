"""Turn the sim's hidden deltas into one-line player-facing consequences."""

AXES = ("trust", "friendship", "hostility", "respect")
THRESHOLD = 5
SHORT_NAMES = {
    "professor": "Webb",
    "friend": "Batman",
    "ta": "Kevin",
}


def short_name(npc_id: str | None) -> str:
    if not npc_id:
        return ""
    return SHORT_NAMES.get(npc_id, npc_id)


def snapshot_relationships() -> dict[str, dict]:
    from core.npc_loader import load_all_npcs
    from core.relationship_engine import get_relationship

    return {npc["id"]: dict(get_relationship(npc["id"])) for npc in load_all_npcs()}


def _axis_lines(before: dict, after: dict, npc_id: str | None = None) -> list[str]:
    name = short_name(npc_id or after.get("npc_id") or before.get("npc_id"))
    lines = []
    for axis in AXES:
        try:
            delta = int(after.get(axis, 0) or 0) - int(before.get(axis, 0) or 0)
        except (TypeError, ValueError):
            continue
        if abs(delta) < THRESHOLD:
            continue
        shown = f"+{delta}" if delta > 0 else str(delta)
        if name:
            lines.append(f"{name}'s {axis} {shown}")
        else:
            lines.append(f"{axis} {shown}")
    return lines


def _is_rel(payload: dict) -> bool:
    return isinstance(payload, dict) and "trust" in payload


def format_consequences(before: dict, after: dict, gossip_events: list | None = None) -> list[str]:
    """Human lines for big relationship swings and gossip that just moved."""
    lines: list[str] = []
    before = before or {}
    after = after or {}

    if before and not _is_rel(before):
        npc_ids = list(dict.fromkeys([*before.keys(), *after.keys()]))
        for npc_id in npc_ids:
            lines.extend(_axis_lines(before.get(npc_id, {}), after.get(npc_id, {}), npc_id))
    else:
        lines.extend(_axis_lines(before, after))

    speakers = []
    for event in gossip_events or []:
        speaker = event.get("from") or event.get("from_npc_id")
        if speaker and speaker not in speakers:
            speakers.append(speaker)
            who = short_name(speaker)
            lines.append(f"{who} might talk" if who else "Someone might talk")

    seen = []
    for line in lines:
        if line and line not in seen:
            seen.append(line)
    return seen

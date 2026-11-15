"""Track student promises so NPCs notice when they are kept or ghosted."""

from core.database import get_connection
from core.memory_manager import save_memory
from core.relationship_engine import update_relationship

PROMISE_GRACE_TICKS = 3
KEPT_TRUST = 4
BROKEN_TRUST = -8
VALID_STATUS = {"pending", "kept", "broken"}


def _tick() -> int:
    from core.gossip_engine import get_tick
    return get_tick()


def create_promise(npc_id: str, content: str, memory_id: int | None = None, due_in: int = PROMISE_GRACE_TICKS) -> dict:
    content = (content or "").strip()
    if not npc_id or not content:
        return {}
    created = _tick()
    due = created + max(1, due_in)
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO promises (npc_id, content, status, created_tick, due_tick, memory_id)
        VALUES (?, ?, 'pending', ?, ?, ?)
        """,
        (npc_id, content, created, due, memory_id),
    )
    promise_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": promise_id,
        "npc_id": npc_id,
        "content": content,
        "status": "pending",
        "created_tick": created,
        "due_tick": due,
        "memory_id": memory_id,
    }


def get_pending_promises(npc_id: str | None = None) -> list[dict]:
    conn = get_connection()
    if npc_id:
        rows = conn.execute(
            "SELECT * FROM promises WHERE npc_id = ? AND status = 'pending' ORDER BY due_tick ASC, id ASC",
            (npc_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM promises WHERE status = 'pending' ORDER BY due_tick ASC, id ASC"
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_promises(npc_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM promises WHERE npc_id = ? ORDER BY id DESC",
        (npc_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def format_pending_promises(npc_id: str) -> str:
    pending = get_pending_promises(npc_id)
    if not pending:
        return "This student has no open promises with you."
    tick = _tick()
    lines = []
    for promise in pending:
        remaining = int(promise["due_tick"]) - tick
        when = "overdue" if remaining <= 0 else f"due in {remaining} period{'s' if remaining != 1 else ''}"
        lines.append(f"- ({when}) {promise['content']}")
    return "\n".join(lines)


def resolve_promise(npc_id: str, status: str, memory_id: int | None = None) -> list[dict]:
    """Mark this NPC's pending promises kept or broken from a conversation."""
    status = (status or "").strip().lower()
    if status not in {"kept", "broken"}:
        return []
    pending = get_pending_promises(npc_id)
    if not pending:
        return []
    resolved = []
    for promise in pending:
        resolved.append(_set_status(promise, status, memory_id))
    return resolved


def maybe_track_from_turn(npc_id: str, result: dict, memory_id: int | None = None) -> list[dict]:
    """Apply parser promise_status, or open a new promise from a promise memory."""
    status = str(result.get("promise_status") or "").strip().lower()
    kind = str(result.get("memory_kind") or "fact").lower().strip()
    tags = str(result.get("memory_tags") or "").lower()
    note = (result.get("memory_note") or "").strip()

    if status in {"kept", "broken"}:
        return resolve_promise(npc_id, status, memory_id)

    tag_tokens = {part.strip() for part in tags.split(",") if part.strip()}
    if kind == "promise" and "kept" in tag_tokens:
        return resolve_promise(npc_id, "kept", memory_id)
    if kind == "promise" and "broken" in tag_tokens:
        return resolve_promise(npc_id, "broken", memory_id)

    if kind == "promise" and note:
        created = create_promise(npc_id, note, memory_id=memory_id)
        return [created] if created else []
    return []


def resolve_overdue_promises() -> list[dict]:
    """Ghosted promises break after the due tick if they are still pending."""
    tick = _tick()
    pending = get_pending_promises()
    broken = []
    for promise in pending:
        if int(promise["due_tick"]) <= tick:
            broken.append(_set_status(promise, "broken"))
    return broken


def clear_promises(npc_id: str | None = None) -> None:
    conn = get_connection()
    if npc_id:
        conn.execute("DELETE FROM promises WHERE npc_id = ?", (npc_id,))
    else:
        conn.execute("DELETE FROM promises")
    conn.commit()
    conn.close()


def _set_status(promise: dict, status: str, memory_id: int | None = None) -> dict:
    conn = get_connection()
    conn.execute(
        "UPDATE promises SET status = ?, memory_id = COALESCE(?, memory_id) WHERE id = ?",
        (status, memory_id, promise["id"]),
    )
    conn.commit()
    conn.close()

    npc_id = promise["npc_id"]
    content = promise["content"]
    if status == "kept":
        update_relationship(npc_id, {"trust": KEPT_TRUST, "respect": 2})
        save_memory(
            npc_id,
            f"Student kept their promise: {content}",
            importance=7,
            tags="promise,kept",
            kind="favor",
        )
    elif status == "broken":
        update_relationship(npc_id, {"trust": BROKEN_TRUST, "hostility": 4})
        save_memory(
            npc_id,
            f"Student broke their promise: {content}",
            importance=8,
            tags="promise,broken",
            kind="grievance",
        )
    updated = {**promise, "status": status}
    if memory_id:
        updated["memory_id"] = memory_id
    return updated

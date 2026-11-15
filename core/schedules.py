"""Who is where, and whether they can actually talk."""

import json
from functools import lru_cache

from config.settings import SCHEDULES_PATH
from core.clock import get_clock
from core.npc_loader import load_npc


@lru_cache(maxsize=1)
def _load() -> dict:
    with open(SCHEDULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def locations() -> list[str]:
    return list(_load().get("locations", []))


def current_slot(npc_id: str, clock: dict | None = None) -> dict | None:
    clock = clock or get_clock()
    for slot in _load().get("schedules", {}).get(npc_id, []):
        if slot.get("weekday") == clock["weekday"] and slot.get("period") == clock["period"]:
            return dict(slot)
    return None


def is_interruptible(npc_id: str, clock: dict | None = None) -> bool:
    slot = current_slot(npc_id, clock)
    return bool(slot and slot.get("interruptible"))


def npcs_at(location: str, clock: dict | None = None) -> list[str]:
    clock = clock or get_clock()
    here = []
    for npc_id, slots in _load().get("schedules", {}).items():
        for slot in slots:
            if (
                slot.get("weekday") == clock["weekday"]
                and slot.get("period") == clock["period"]
                and slot.get("location") == location
            ):
                here.append(npc_id)
    return here


def unavailable_line(npc_id: str, clock: dict | None = None) -> str:
    npc = load_npc(npc_id)
    name = npc["name"]
    slot = current_slot(npc_id, clock)
    if not slot:
        notes = {
            "professor": f"{name} has gone home. A typed note on the office door says office hours are afternoons.",
            "ta": f"{name} isn't at the cubicle. A sticky note: 'If this is a 2am email, the answer is still no.'",
            "friend": f"{name} isn't around. Someone in the hallway says he was last seen filming something.",
        }
        return notes.get(npc_id, f"{name} isn't around right now. Try another period.")
    location = slot.get("location", "campus")
    if slot.get("interruptible"):
        return ""
    if npc_id == "professor":
        return (
            f"{name} is at {location} and not taking visitors. "
            "He clocks you, raises one finger without stopping, and keeps moving."
        )
    if npc_id == "ta":
        return (
            f"{name} is at {location}, headphones on, drowning in a grading queue. "
            "He mouths 'later' and points at the sign that says do not interrupt."
        )
    return (
        f"You catch {name} at {location} in passing. "
        "He is mid-bit with someone else and waves you off — later, bro."
    )


def format_location_for_prompt(npc_id: str, clock: dict | None = None) -> str:
    slot = current_slot(npc_id, clock)
    if not slot:
        return "You are not currently somewhere a student can sit down with you."
    busy = "You can talk." if slot.get("interruptible") else "You cannot have a real conversation right now."
    return f"You are at {slot['location']}. {busy}"

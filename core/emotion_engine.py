from core.database import get_connection
from config.settings import STAT_MIN, STAT_MAX

EMOTION_KEYS = ["happy", "angry", "suspicious", "stressed", "excited", "annoyed"]


def get_emotions(npc_id: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT happy, angry, suspicious, stressed, excited, annoyed FROM emotions WHERE npc_id = ?",
        (npc_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {k: 0 for k in EMOTION_KEYS}


def update_emotions(npc_id: str, deltas: dict) -> None:
    current = get_emotions(npc_id)
    updates = {}
    for key in EMOTION_KEYS:
        delta = deltas.get(key, 0)
        updates[key] = max(STAT_MIN, min(STAT_MAX, current.get(key, 0) + delta))

    conn = get_connection()
    conn.execute("""
        UPDATE emotions
        SET happy=?, angry=?, suspicious=?, stressed=?, excited=?, annoyed=?, updated_at=CURRENT_TIMESTAMP
        WHERE npc_id=?
    """, (
        updates["happy"], updates["angry"], updates["suspicious"],
        updates["stressed"], updates["excited"], updates["annoyed"],
        npc_id
    ))
    conn.commit()
    conn.close()


def mood_for_prompt(npc_id: str, emotions: dict, clock: dict | None = None) -> dict:
    """Temporary schedule modifiers for the prompt only — never written back."""
    from core.clock import get_clock

    clock = clock or get_clock()
    mood = {key: int(emotions.get(key, 0) or 0) for key in EMOTION_KEYS}
    week = int(clock.get("week") or 6)
    weekday = clock.get("weekday") or "thursday"
    period = clock.get("period") or "afternoon"

    if npc_id == "ta" and (period in {"evening", "night"} or weekday in {"thursday", "friday"} or week >= 6):
        mood["stressed"] += 15
        mood["annoyed"] += 8
        mood["happy"] -= 5
    if npc_id == "friend" and weekday == "friday" and period == "evening":
        mood["excited"] += 20
        mood["happy"] += 10
    if npc_id == "professor" and week >= 6:
        mood["annoyed"] += 12
        mood["stressed"] += 8
        mood["happy"] -= 4

    for key in EMOTION_KEYS:
        mood[key] = max(STAT_MIN, min(STAT_MAX, mood[key]))
    return mood


def mood_caption(npc_id: str, clock: dict | None = None) -> str:
    from core.clock import get_clock

    clock = clock or get_clock()
    weekday = clock.get("weekday")
    period = clock.get("period")
    week = int(clock.get("week") or 6)
    if npc_id == "ta" and (period in {"evening", "night"} or weekday in {"thursday", "friday"} or week >= 6):
        return "Grading is sitting on him. Stress is up for this period."
    if npc_id == "friend" and weekday == "friday" and period == "evening":
        return "Friday evening in The Dungeon. He's buzzing."
    if npc_id == "professor" and week >= 6:
        return "Midterm week. His patience is thinner than usual."
    return ""


def reset_emotions(npc_id: str, mood: dict) -> None:
    values = (
        npc_id,
        mood.get("happy", 50),
        mood.get("angry", 0),
        mood.get("suspicious", 0),
        mood.get("stressed", 30),
        mood.get("excited", 40),
        mood.get("annoyed", 0),
    )
    conn = get_connection()
    conn.execute("""
        INSERT INTO emotions (npc_id, happy, angry, suspicious, stressed, excited, annoyed, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(npc_id) DO UPDATE SET
            happy=excluded.happy,
            angry=excluded.angry,
            suspicious=excluded.suspicious,
            stressed=excluded.stressed,
            excited=excluded.excited,
            annoyed=excluded.annoyed,
            updated_at=CURRENT_TIMESTAMP
    """, values)
    conn.commit()
    conn.close()

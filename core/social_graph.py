"""NPC opinions, campus facts, and who knows what."""

from core.database import get_connection
from config.settings import STAT_MAX, STAT_MIN
from core.npc_loader import load_opinion_seeds

KNOWLEDGE_STATUSES = ("known", "rumor", "denied")


def get_opinion(npc_id: str, other_npc_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """
        SELECT npc_id, other_npc_id, trust, respect, irritation, note
        FROM npc_opinions
        WHERE npc_id = ? AND other_npc_id = ?
        """,
        (npc_id, other_npc_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_opinions(npc_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT npc_id, other_npc_id, trust, respect, irritation, note
        FROM npc_opinions
        WHERE npc_id = ?
        ORDER BY other_npc_id
        """,
        (npc_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_opinion(
    npc_id: str,
    other_npc_id: str,
    trust: int,
    respect: int,
    irritation: int,
    note: str = "",
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO npc_opinions (npc_id, other_npc_id, trust, respect, irritation, note, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(npc_id, other_npc_id) DO UPDATE SET
            trust=excluded.trust,
            respect=excluded.respect,
            irritation=excluded.irritation,
            note=excluded.note,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            npc_id,
            other_npc_id,
            _clamp(trust),
            _clamp(respect),
            _clamp(irritation),
            note,
        ),
    )
    conn.commit()
    conn.close()


def reset_opinions(npc_id: str | None = None) -> None:
    seeds = load_opinion_seeds()
    conn = get_connection()
    if npc_id:
        conn.execute("DELETE FROM npc_opinions WHERE npc_id = ?", (npc_id,))
        seeds = [s for s in seeds if s["npc_id"] == npc_id]
    else:
        conn.execute("DELETE FROM npc_opinions")
    for seed in seeds:
        conn.execute(
            """
            INSERT INTO npc_opinions (npc_id, other_npc_id, trust, respect, irritation, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                seed["npc_id"],
                seed["other_npc_id"],
                seed["trust"],
                seed["respect"],
                seed["irritation"],
                seed.get("note", ""),
            ),
        )
    conn.commit()
    conn.close()


def create_fact(
    fact_text: str,
    source_npc_id: str | None = None,
    about_player: bool = True,
    about_npc_id: str | None = None,
    sensitivity: int = 40,
    keep_secret: bool = False,
    distorted_text: str = "",
) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO campus_facts (
            fact_text, source_npc_id, about_player, about_npc_id,
            sensitivity, keep_secret, distorted_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fact_text,
            source_npc_id,
            1 if about_player else 0,
            about_npc_id,
            _clamp(sensitivity),
            1 if keep_secret else 0,
            distorted_text,
        ),
    )
    fact_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return int(fact_id)


def get_fact(fact_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM campus_facts WHERE id = ?", (fact_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_recent_facts(limit: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM campus_facts ORDER BY created_at DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def grant_knowledge(npc_id: str, fact_id: int, status: str = "known", hop: int = 0) -> None:
    if status not in KNOWLEDGE_STATUSES:
        raise ValueError(f"Unknown knowledge status: {status}")
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO npc_knowledge (npc_id, fact_id, status, hop, learned_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(npc_id, fact_id) DO UPDATE SET
            status=excluded.status,
            hop=excluded.hop,
            learned_at=CURRENT_TIMESTAMP
        """,
        (npc_id, fact_id, status, hop),
    )
    conn.commit()
    conn.close()


def get_knowledge_for_npc(npc_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT k.npc_id, k.fact_id, k.status, k.hop, k.learned_at,
               f.fact_text, f.source_npc_id, f.about_player, f.about_npc_id,
               f.sensitivity, f.keep_secret, f.distorted_text
        FROM npc_knowledge k
        JOIN campus_facts f ON f.id = k.fact_id
        WHERE k.npc_id = ?
        ORDER BY k.learned_at DESC
        """,
        (npc_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_knowledge(npc_id: str | None = None) -> None:
    conn = get_connection()
    if npc_id:
        conn.execute("DELETE FROM npc_knowledge WHERE npc_id = ?", (npc_id,))
    else:
        conn.execute("DELETE FROM npc_knowledge")
    conn.commit()
    conn.close()


def clear_facts() -> None:
    conn = get_connection()
    conn.execute("DELETE FROM npc_knowledge")
    conn.execute("DELETE FROM campus_facts")
    conn.commit()
    conn.close()


def _clamp(value: int) -> int:
    return max(STAT_MIN, min(STAT_MAX, int(value)))

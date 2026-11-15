from core.database import get_connection

DEFAULT_PLAYER = {
    "display_name": "Student",
    "year": "junior",
    "notes": "",
    "introduced": 0,
}


def get_player() -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT display_name, year, notes, introduced FROM players WHERE id = 1"
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT OR IGNORE INTO players (id, display_name, year, introduced) VALUES (1, 'Student', 'junior', 0)"
        )
        conn.commit()
        conn.close()
        return dict(DEFAULT_PLAYER)
    conn.close()
    return dict(row)


def save_player(display_name: str, year: str = "junior", notes: str = "") -> dict:
    name = (display_name or "").strip() or "Student"
    year = (year or "junior").strip() or "junior"
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO players (id) VALUES (1)")
    conn.execute(
        """
        UPDATE players
        SET display_name = ?, year = ?, notes = ?, introduced = 1
        WHERE id = 1
        """,
        (name, year, notes),
    )
    conn.commit()
    conn.close()
    return get_player()


def player_label(player: dict | None = None) -> str:
    player = player or get_player()
    name = player.get("display_name") or "Student"
    year = player.get("year") or "junior"
    return f"{name}, a {year} CS student"


def format_player_for_prompt(player: dict | None = None) -> str:
    player = player or get_player()
    name = player.get("display_name") or "Student"
    year = player.get("year") or "junior"
    if not player.get("introduced"):
        return (
            "This student has not given you a name yet. You may ask, or Batman may invent a nickname. "
            "Do not assume a legal name."
        )
    return (
        f"This student's name is {name}. They are a {year} CS student at Westbrook. "
        f"Use their name naturally. Batman may still invent a nickname on top of it."
    )

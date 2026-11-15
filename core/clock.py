"""Simulated campus time. Tick 0 is Week 6, Thursday afternoon."""

from core.database import get_connection

PERIODS = ("morning", "afternoon", "evening", "night")
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")
START_WEEK = 6
START_WEEKDAY = "thursday"
START_PERIOD = "afternoon"
FINAL_WEEK = 12


def clock_from_tick(tick: int) -> dict:
    tick = max(0, int(tick or 0))
    start_period = PERIODS.index(START_PERIOD)
    start_weekday = WEEKDAYS.index(START_WEEKDAY)
    total_periods = start_period + tick
    period = PERIODS[total_periods % len(PERIODS)]
    total_days = total_periods // len(PERIODS)
    weekday_index = (start_weekday + total_days) % len(WEEKDAYS)
    weeks_passed = (start_weekday + total_days) // len(WEEKDAYS)
    week = START_WEEK + weeks_passed
    return {
        "tick": tick,
        "week": week,
        "weekday": WEEKDAYS[weekday_index],
        "period": period,
    }


def sync_clock(tick: int | None = None) -> dict:
    if tick is None:
        from core.gossip_engine import get_tick
        tick = get_tick()
    clock = clock_from_tick(tick)
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO campus_state (id, tick) VALUES (1, 0)")
    conn.execute(
        """
        UPDATE campus_state
        SET tick = ?, week = ?, weekday = ?, period = ?
        WHERE id = 1
        """,
        (clock["tick"], clock["week"], clock["weekday"], clock["period"]),
    )
    conn.commit()
    conn.close()
    return clock


def get_clock() -> dict:
    from core.gossip_engine import get_tick
    return sync_clock(get_tick())


def format_clock(clock: dict | None = None) -> str:
    clock = clock or get_clock()
    return f"Week {clock['week']} · {clock['weekday'].title()} {clock['period']}"


def format_clock_for_prompt(clock: dict | None = None) -> str:
    clock = clock or get_clock()
    return (
        f"It is {clock['weekday'].title()} {clock['period']}, week {clock['week']} of the semester. "
        "Treat this as the current time. Do not invent a different day."
    )


def ticks_until_next_morning() -> int:
    clock = get_clock()
    period_index = PERIODS.index(clock["period"])
    return len(PERIODS) - period_index


def advance_period() -> list[dict]:
    """One period passes. Single time source: advance_and_resolve."""
    from core.gossip_engine import advance_and_resolve
    return advance_and_resolve()


def skip_day() -> list[dict]:
    """Advance to the next weekday morning, resolving gossip and promises along the way."""
    delivered = []
    for _ in range(ticks_until_next_morning()):
        delivered.extend(advance_period())
    return delivered


def reset_clock() -> dict:
    from core.database import get_connection

    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO campus_state (id, tick) VALUES (1, 0)")
    conn.execute("UPDATE campus_state SET tick = 0 WHERE id = 1")
    conn.commit()
    conn.close()
    return sync_clock(0)


def is_finals_week(clock: dict | None = None) -> bool:
    clock = clock or get_clock()
    if clock["week"] > FINAL_WEEK:
        return True
    if clock["week"] == FINAL_WEEK:
        return True
    if clock["week"] == FINAL_WEEK - 1 and clock["weekday"] == "friday" and clock["period"] == "night":
        return True
    return False

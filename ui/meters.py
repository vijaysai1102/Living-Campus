import streamlit as st

_EMOTION_META = {
    "happy":      ("😊", "#22c55e"),
    "angry":      ("😠", "#ef4444"),
    "suspicious": ("🤨", "#eab308"),
    "stressed":   ("😰", "#f97316"),
    "excited":    ("🤩", "#3b82f6"),
    "annoyed":    ("😒", "#a855f7"),
}

_REL_META = {
    "trust":      ("🤝", "#06b6d4"),
    "friendship": ("💛", "#facc15"),
    "hostility":  ("⚔️",  "#f43f5e"),
    "respect":    ("🎖️",  "#8b5cf6"),
}

KIND_META = {
    "fact":      ("fact", "📝", "#64748b"),
    "promise":   ("promise", "🤝", "#22c55e"),
    "secret":    ("secret", "🔒", "#c084fc"),
    "grievance": ("grievance", "💢", "#f43f5e"),
    "favor":     ("favor", "🙏", "#38bdf8"),
}
TIMELINE_FILTERS = ("all", "promise", "secret", "grievance")


def filter_timeline_memories(memories: list[dict], kind: str = "all") -> list[dict]:
    if not kind or kind == "all":
        return list(memories)
    return [m for m in memories if (m.get("kind") or "fact") == kind]


def format_timeline_entry(memory: dict) -> dict:
    kind = (memory.get("kind") or "fact").lower()
    label, emoji, color = KIND_META.get(kind, KIND_META["fact"])
    importance = int(memory.get("importance") or 5)
    ts = memory.get("created_at") or ""
    if "T" in ts:
        ts = ts.replace("T", " ")[:16]
    elif " " in ts:
        ts = ts[:16]
    return {
        "kind": kind,
        "badge": label,
        "emoji": emoji,
        "color": color,
        "star": importance >= 7,
        "lock": kind == "secret",
        "timestamp": ts,
        "content": memory.get("content") or "",
        "importance": importance,
    }


def _bar(label: str, emoji: str, value: int, color: str) -> None:
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;margin-bottom:2px">'
        f'<span style="font-size:0.8rem">{emoji} {label.capitalize()}</span>'
        f'<span style="font-size:0.8rem;color:{color}">{value}</span>'
        f'</div>',
        unsafe_allow_html=True
    )
    filled = int((value / 100) * 20)
    bar = "█" * filled + "░" * (20 - filled)
    st.markdown(
        f'<div style="font-family:monospace;font-size:0.7rem;color:{color};margin-bottom:8px">{bar}</div>',
        unsafe_allow_html=True
    )


def render_meters(emotions: dict, relationship: dict) -> None:
    st.markdown("**Emotional State**")
    for key, (emoji, color) in _EMOTION_META.items():
        val = emotions.get(key, 0)
        _bar(key, emoji, val, color)

    st.divider()
    st.markdown("**Relationship**")
    for key, (emoji, color) in _REL_META.items():
        val = relationship.get(key, 0)
        _bar(key, emoji, val, color)

    interactions = relationship.get("interactions_count", 0)
    st.caption(f"Total interactions: {interactions}")


def render_memory_timeline(memories: list[dict]) -> None:
    st.divider()
    with st.expander("🧠 Memory Timeline", expanded=False):
        if not memories:
            st.caption("No memories yet. Start talking!")
            return
        kind_filter = st.radio(
            "Memory kind",
            list(TIMELINE_FILTERS),
            horizontal=True,
            label_visibility="collapsed",
            key="memory_kind_filter",
        )
        visible = filter_timeline_memories(memories, kind_filter)
        if not visible:
            st.caption(f"No {kind_filter} memories yet.")
            return
        for memory in reversed(visible):
            entry = format_timeline_entry(memory)
            star = "⭐" if entry["star"] else entry["emoji"]
            badge_bg = "#3b0764" if entry["lock"] else "#1e293b"
            st.markdown(
                f'<div style="border-left:3px solid {entry["color"]};padding:4px 8px;margin-bottom:6px;'
                f'background:{"#2e1064" if entry["lock"] else "transparent"}">'
                f'<div style="font-size:0.7rem;color:#94a3b8;display:flex;gap:6px;align-items:center">'
                f'{star} {entry["timestamp"]}'
                f'<span style="background:{badge_bg};color:{entry["color"]};padding:1px 6px;'
                f'border-radius:8px;font-size:0.65rem">{entry["emoji"]} {entry["badge"]}</span>'
                f'</div>'
                f'<div style="font-size:0.82rem;color:{"#e9d5ff" if entry["lock"] else "inherit"}">'
                f'{entry["content"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

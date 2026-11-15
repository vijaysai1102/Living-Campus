import streamlit as st
from core.story_engine import journal_data


def render_journal() -> None:
    data = journal_data()
    with st.expander("📓 Journal", expanded=False):
        st.caption("What you actually know. Not a god log.")
        st.markdown("**Open favors**")
        if data["favors"]:
            for favor in data["favors"]:
                st.markdown(f"- {favor.get('title')} _{favor.get('status')}_")
        else:
            st.caption("No one has asked you for anything yet.")
        st.markdown("**Secrets**")
        if data["secrets"]:
            for secret in data["secrets"]:
                st.markdown(f"- {secret['title']} ({secret['state']}) — {secret['hint']}")
        else:
            st.caption("You have not confirmed any secrets.")
        st.markdown("**Upcoming deadlines**")
        if data["deadlines"]:
            for item in data["deadlines"]:
                st.markdown(f"- {item['title']} (week {item['due_week']})")
        else:
            st.caption("Nothing urgent on the calendar.")

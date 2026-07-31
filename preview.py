"""Preview components for timetable results."""

import streamlit as st


def render_preview(data: dict) -> None:
    """Render a placeholder preview table."""
    st.subheader("Preview")
    st.json(data)

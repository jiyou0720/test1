"""Sidebar components for the Streamlit UI."""

import streamlit as st


def render_sidebar() -> None:
    """Render basic sidebar controls."""
    with st.sidebar:
        st.header("Options")
        st.checkbox("Allow conflicts", value=False)

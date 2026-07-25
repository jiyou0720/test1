"""Streamlit application entry point."""

import streamlit as st


def run_app() -> None:
    """Render the main page."""
    st.set_page_config(page_title="TimetableGenerator")
    st.title("TimetableGenerator")
    st.write("Project scaffold is ready.")

"""Reusable Streamlit UI components."""

import streamlit as st


def info_box(message: str) -> None:
    """Display a helpful info box."""
    st.info(message)

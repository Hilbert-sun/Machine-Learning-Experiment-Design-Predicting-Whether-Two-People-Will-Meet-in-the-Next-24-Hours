"""Streamlit entry point for Encounter Lab."""

import streamlit as st

from src.ui import PAGES

st.set_page_config(page_title="Encounter Lab · 相遇实验室", page_icon="🔬", layout="wide")
navigation = st.navigation(
    [st.Page(path, title=title, default=index == 0) for index, (path, title) in enumerate(PAGES)],
    position="top",
)
navigation.run()

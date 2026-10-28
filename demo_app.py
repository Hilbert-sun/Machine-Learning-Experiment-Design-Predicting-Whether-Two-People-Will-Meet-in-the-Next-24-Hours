"""Public online-demo entry point: the normal app with research tools locked (fail-closed).

Two layers: this entry blocks locked routes before navigation runs, and every locked page also calls
src.demo_mode.stop_if_locked, because a cold server's first request can be routed through Streamlit's
legacy pages/ directory and run a page file without this entry script.
"""

import streamlit as st

from src.demo_mode import DEMO_PAGES, SESSION_FLAG, render_unavailable
from src.ui import PAGES, primary_navigation

st.session_state[SESSION_FLAG] = True
st.set_page_config(page_title="Encounter Lab · 相遇实验室", page_icon="🔬", layout="wide")
navigation = st.navigation(
    [st.Page(path, title=title, default=index == 0) for index, (path, title) in enumerate(PAGES)],
    position="hidden",
)
from src.welcome import render_welcome

primary_navigation()
render_welcome()
current = {title: path for path, title in PAGES}[navigation.title]
if current not in DEMO_PAGES:
    render_unavailable(navigation.title)
else:
    navigation.run()

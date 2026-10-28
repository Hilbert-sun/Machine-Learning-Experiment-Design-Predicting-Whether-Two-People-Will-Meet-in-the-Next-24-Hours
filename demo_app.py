"""Public online-demo entry point: the normal app with research tools locked (fail-closed)."""

from pathlib import Path
import runpy

import streamlit as st

from src.demo_mode import SESSION_FLAG

st.session_state[SESSION_FLAG] = True
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")

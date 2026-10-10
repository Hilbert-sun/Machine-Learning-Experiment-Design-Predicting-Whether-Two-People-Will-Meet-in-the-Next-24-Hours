from pathlib import Path

import streamlit as st
import yaml

from src.time_machine_ui import render_time_machine

st.title('时间机器 · Time Machine')
root=Path(__file__).resolve().parents[1]
config=yaml.safe_load((root/'configs/default.yaml').read_text())
render_time_machine(root,config)

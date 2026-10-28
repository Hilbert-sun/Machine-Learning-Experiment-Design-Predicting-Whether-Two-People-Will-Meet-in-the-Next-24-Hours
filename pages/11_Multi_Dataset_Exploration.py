from src.demo_mode import stop_if_locked

stop_if_locked(__file__)  # public demo: refuse before any import or work
from pathlib import Path

from src.multisource_ui import render

render(Path(__file__).resolve().parents[1])

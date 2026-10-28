"""Public demo entry locks every page that needs local data or starts server-side work."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.demo_mode import DEMO_PAGES
from src.ui import PAGES

ROOT = Path(__file__).resolve().parents[1]
DEMO = str(ROOT / 'demo_app.py')


@pytest.fixture(autouse=True)
def modern_router(monkeypatch, tmp_path):
    import yaml
    from streamlit.runtime.pages_manager import PagesManager
    original_init = PagesManager.__init__
    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        PagesManager.uses_pages_directory = False
    monkeypatch.setattr(PagesManager, '__init__', init)
    config = yaml.safe_load((ROOT / 'configs/default.yaml').read_text())
    config['paths'] = {key: str(tmp_path / key) for key in config['paths']}
    monkeypatch.setattr(yaml, 'safe_load', lambda _: config)
    monkeypatch.delenv('ENCOUNTER_DEMO_MODE', raising=False)


def notice(app):
    return any('在线演示只开放' in item.value for item in app.info)


@pytest.mark.parametrize('page,_title', PAGES)
def test_demo_entry_blocks_local_research_pages(page, _title):
    app = AppTest.from_file(DEMO, default_timeout=15).run().switch_page(page).run()
    assert not app.exception
    assert notice(app) == (page not in DEMO_PAGES)
    if page not in DEMO_PAGES:
        assert not app.button and not app.selectbox  # no download/train/select controls render


def test_demo_set_is_public_only_and_normal_app_unchanged():
    assert DEMO_PAGES == {PAGES[i][0] for i in (0, 7, 12, 13, 14)}
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=15).run().switch_page('pages/1_Data_Manager.py').run()
    assert not app.exception and not notice(app)

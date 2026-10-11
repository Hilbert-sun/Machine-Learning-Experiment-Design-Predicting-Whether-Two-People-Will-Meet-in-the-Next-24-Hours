"""P03 native navigation and lazy research entry, independent of private artifacts."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.ui import PAGES, PRIMARY_PAGES, RESEARCH_GROUPS

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / 'app.py')
HUB = 'pages/14_Research_Hub.py'


@pytest.fixture(autouse=True)
def no_private_paths(monkeypatch, tmp_path):
    import yaml
    from streamlit.runtime.pages_manager import PagesManager
    # AppTest resets v1 directory detection on each run despite our v2 router.
    # Keep the real app entrypoint active, as in a persistent browser session.
    original_init = PagesManager.__init__
    def modern_router(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        PagesManager.uses_pages_directory = False
    monkeypatch.setattr(PagesManager, '__init__', modern_router)
    config = yaml.safe_load((ROOT / 'configs/default.yaml').read_text())
    config['paths'] = {key: str(tmp_path / key) for key in config['paths']}
    monkeypatch.setattr(yaml, 'safe_load', lambda _: config)


def test_four_entries_and_all_research_routes_remain_registered():
    assert len(PRIMARY_PAGES) == 4
    assert {p for p, _, _ in PRIMARY_PAGES} == {PAGES[i][0] for i in (0, 12, 13, 14)}
    assert sorted(index for _, entries in RESEARCH_GROUPS for index, _ in entries) == list(range(1, 12))
    assert len(PAGES) == 15 and len({p for p, _ in PAGES}) == 15
    assert 'position="hidden"' in (ROOT / 'app.py').read_text()


@pytest.mark.parametrize('page,_title', PAGES)
def test_global_navigation_on_every_registered_page(page, _title):
    app = AppTest.from_file(APP, default_timeout=15).run().switch_page(page).run()
    assert not app.exception
    links = app.get('page_link')
    assert [link.proto.label for link in links[:4]] == [label for _, label, _ in PRIMARY_PAGES]
    assert all(not link.proto.disabled for link in links[:4])
    app.switch_page(PAGES[0][0]).run()
    assert not app.exception and '相遇实验室' in app.title[0].value
    assert not app.metric


def test_home_and_hub_are_lazy_even_after_research_was_open(monkeypatch):
    import pandas as pd
    import src.loader as loader
    from src.model_registry import ModelRegistry
    def forbidden(*args, **kwargs): pytest.fail('Passive directory scanned or loaded private artifacts.')
    monkeypatch.setattr(loader, 'supported_files', forbidden)
    monkeypatch.setattr(pd, 'read_parquet', forbidden)
    monkeypatch.setattr(ModelRegistry, 'load', forbidden)
    app = AppTest.from_file(APP).run()
    assert not app.exception and not app.metric
    next(b for b in app.button if b.label == '进入科研中心').click().run()
    assert not app.exception and not app.metric
    labels = {link.proto.label for link in app.get('page_link')}
    assert {label for _, label in PAGES[1:12]} <= labels
    app.session_state['_overview_research_open'] = True
    app.switch_page(PAGES[0][0]).run()
    assert not app.exception and not app.metric


@pytest.mark.parametrize('label,target', [('开始偶遇预测', 12), ('探索相遇的规律', 13), ('进入科研中心', 14)])
def test_home_buttons_reach_real_registered_targets(label, target):
    app = AppTest.from_file(APP).run()
    next(b for b in app.button if b.label == label).click().run()
    assert not app.exception and app.title[0].value == PAGES[target][1]

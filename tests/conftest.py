"""No test may reuse another fixture's private T32 cache or pollute real artifacts."""

import pytest


@pytest.fixture(autouse=True)
def forbid_live_http_in_tests(monkeypatch):
    """Package/scanner installation is outside pytest; dataset HTTP must be mocked."""
    import importlib.util
    import urllib.request
    def forbidden(*args,**kwargs):
        raise AssertionError('Live HTTP is forbidden in tests; use synthetic fixtures or explicit mocks.')
    monkeypatch.setattr(urllib.request,'urlopen',forbidden)
    if importlib.util.find_spec('requests') is not None:
        import requests
        monkeypatch.setattr(requests.sessions.Session,'request',forbidden)


@pytest.fixture(autouse=True)
def isolate_private_cache(monkeypatch, tmp_path):
    monkeypatch.setenv('ENCOUNTER_CACHE_ROOT', str(tmp_path/'private_t32_cache'))

"""No test may reuse another fixture's private T32 cache or pollute real artifacts."""

import pytest


@pytest.fixture(autouse=True)
def isolate_private_cache(monkeypatch, tmp_path):
    monkeypatch.setenv('ENCOUNTER_CACHE_ROOT', str(tmp_path/'private_t32_cache'))

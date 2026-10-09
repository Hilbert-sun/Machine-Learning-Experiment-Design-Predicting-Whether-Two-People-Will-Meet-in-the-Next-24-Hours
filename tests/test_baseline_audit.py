import json

import pytest

from src.baseline_audit import immutable_json, sha256, verify_frozen
from src.feature_policy import feature_window_view
import pandas as pd


def test_frozen_manifest_is_idempotent_and_rejects_replacement_or_tampering(tmp_path):
    source = tmp_path / "evidence"
    source.write_text("original")
    record = {"file_hashes": {"evidence": sha256(source)}}
    path = immutable_json(tmp_path / "freeze.json", record)
    assert immutable_json(path, record) == path
    assert verify_frozen(tmp_path, path)
    with pytest.raises(ValueError, match="Frozen manifest differs"):
        immutable_json(path, {"changed": True})
    source.write_text("replacement")
    with pytest.raises(ValueError, match="changed"):
        verify_frozen(tmp_path, path)


def test_legacy_e2_masks_long_features_but_frequency_1d_becomes_unavailable():
    frame = pd.DataFrame({"contact_count_1d": [2], "contact_count_3d": [4], "contact_count_14d": [9],
                          "common_neighbors_historical": [3], "scan_coverage_a": [0.9],
                          "historical_contact_probability": [0.7], "time_since_last_contact": [5*86400]})
    view = feature_window_view(frame, 1)
    assert view.contact_count_1d.iloc[0] == 2
    assert view.drop(columns="contact_count_1d").isna().all().all()

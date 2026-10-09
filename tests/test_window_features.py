from dataclasses import replace

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.pipeline_cache import PipelineArtifact
from src.window_features import build_window_features, WINDOW_FEATURES
from test_window_cohort import fixture_processed, DAY


def history(tmp_path, extra=()):
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = fixture_processed(tmp_path)
    path = p.directory / "contacts.parquet"
    original = pq.read_table(path)
    additions = [{"timestamp": t, "source_timestamp": t, "user_min": a, "user_max": b, "rssi": -10.0} for t, a, b in extra]
    frame = pd.concat([original.to_pandas(), pa.Table.from_pylist(additions, schema=original.schema).to_pandas()], ignore_index=True).sort_values("timestamp")
    pq.write_table(pa.Table.from_pandas(frame, schema=original.schema, preserve_index=False), path, row_group_size=3)
    keys = tmp_path / "keys.parquet"
    pd.DataFrame([{"dataset_id": "copenhagen", "timestamp": 12*DAY+28800, "user_min": 1, "user_max": 2}]).to_parquet(keys, index=False)
    return p, PipelineArtifact(keys, {}, False)


def features(p, cohort, output, days):
    artifact = build_window_features(p, cohort, output, history_window_days=days)
    return pd.read_parquet(artifact.path), artifact


def test_older_history_and_future_perturbations_respect_every_feature_budget(tmp_path):
    t = 12*DAY+28800
    base, keys = history(tmp_path / "base")
    five, five_keys = history(tmp_path / "five", [(t-5*DAY, 1, 2), (t-5*DAY, 1, 9), (t-5*DAY, 2, 9)])
    old, old_keys = history(tmp_path / "old", [(t-10*DAY, 1, 2)])
    future, future_keys = history(tmp_path / "future", [(t, 1, 2), (t+1, 1, 9)])
    for days in (1, 3, 7):
        before, _ = features(base, keys, tmp_path/"out-base", days)
        after, _ = features(five, five_keys, tmp_path/"out-five", days)
        if days < 7:
            pd.testing.assert_frame_equal(before, after)
        else:
            assert after.pair_contact_count.iloc[0] > before.pair_contact_count.iloc[0]
            assert after.common_neighbors.iloc[0] > before.common_neighbors.iloc[0]
        pd.testing.assert_frame_equal(before, features(old, old_keys, tmp_path/"out-old", days)[0])
        pd.testing.assert_frame_equal(before, features(future, future_keys, tmp_path/"out-future", days)[0])


def test_resumable_snapshot_cache_and_target_fields_not_read(tmp_path, monkeypatch):
    p, keys = history(tmp_path / "base")
    expected, artifact = features(p, keys, tmp_path/"out", 3)
    assert set(expected.columns) == {"dataset_id", "timestamp", "user_min", "user_max", *WINDOW_FEATURES}
    assert expected.scan_coverage_a.iloc[0] == 1
    assert expected.historical_contact_probability.iloc[0] == 1
    assert features(p, keys, tmp_path/"out", 3)[1].cached
    artifact.path.unlink()  # interrupted/missing final artifact must reuse finished snapshots
    monkeypatch.setattr("src.window_features.bounded_context", lambda *a: pytest.fail("completed snapshot recalculated"))
    pd.testing.assert_frame_equal(expected, features(p, keys, tmp_path/"out", 3)[0])
    frame = pd.read_parquet(keys.path).assign(label_24h=1, future_scan_coverage_a=999)
    changed = tmp_path/"changed.parquet"
    frame.to_parquet(changed, index=False)
    pd.testing.assert_frame_equal(expected, features(p, replace(keys, path=changed), tmp_path/"out", 3)[0])


def test_unknown_scan_and_rssi_and_invalid_windows(tmp_path):
    p, keys = history(tmp_path/"base")
    p.report["scan_coverage_available"] = False
    frame, _ = features(p, keys, tmp_path/"out", 1)
    assert frame[["scan_coverage_a", "scan_coverage_b", "observed_history_days", "historical_contact_probability"]].isna().all().all()
    with pytest.raises(ValueError, match="1/3/7"):
        features(p, keys, tmp_path/"out", 14)

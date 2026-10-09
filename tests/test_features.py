"""Synthetic histories test rolling boundaries and invariance to future changes."""

from dataclasses import replace
import os

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.feature_engineering import FEATURE_NAMES, build_features
from src.label_builder import build_labels
from src.preprocessing import preprocess_contacts

DAY, T = 86400, 8 * 3600


def prepare(tmp_path, extra=()):
    source = tmp_path / "bt_symmetric.csv"
    rows = ["timestamp,user_a,user_b,rssi", "0,5,97,-80", "100,5,97,-60", "200,5,222,-70", "250,97,222,-70"]
    rows += [f"{t},{user},-1,0" for t in range(0, 3 * DAY + 1, 300) for user in (5, 97, 222)]
    rows += [f"{t},{a},{b},{rssi}" for t, a, b, rssi in extra]
    source.write_text("\n".join(rows) + "\n")
    processed = preprocess_contacts(source, "Copenhagen", tmp_path / "processed")
    labels = build_labels(processed, tmp_path / "labels")
    features = build_features(processed, labels, tmp_path / "features")
    return processed, labels, features


def test_rolling_contact_bins_rssi_activity_and_historical_network(tmp_path):
    processed, labels, artifact = prepare(tmp_path, [(T, 5, 97, -20), (T + 1, 5, 333, -10)])
    frame = pd.read_parquet(artifact.path)
    row = frame.loc[frame.timestamp.eq(T) & frame.user_min.eq(5) & frame.user_max.eq(97)].iloc[0]
    assert row.contact_count_1d == row.contact_count_7d == 2
    assert row.contact_bins_1d == 1
    assert row.time_since_last_contact == T - 100
    assert row.unique_contact_days_7d == 1
    assert row.rssi_mean_7d == -70 and row.rssi_max_7d == -60
    assert row.common_neighbors_historical == 1
    assert row.historical_network_degree_a == row.historical_network_degree_b == 2
    assert row.participant_a_activity_7d == row.participant_b_activity_7d == 3
    assert row.scan_coverage_a == pytest.approx(96 / (7 * 288))
    assert row.history_complete_1d == 0
    assert pd.isna(row.historical_contact_probability)
    assert frame.sms_count_7d.isna().all() and frame.call_count_7d.isna().all()
    assert frame.relative_weekday.isna().all() and frame.is_relative_weekend.isna().all()
    assert set(frame.columns) == {"timestamp", "user_min", "user_max", *FEATURE_NAMES}
    assert len(frame) == labels.report["rows"]
    assert build_features(processed, labels, tmp_path / "features").cached


def test_adding_future_events_does_not_change_earlier_features(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    _, _, original = prepare(first)
    _, _, changed = prepare(second, [(T, 5, 97, -1), (T + 1, 5, 333, -10), (T + 2, 97, 333, -10)])
    before = pd.read_parquet(original.path).query("timestamp == @T").reset_index(drop=True)
    after = pd.read_parquet(changed.path).query("timestamp == @T").reset_index(drop=True)
    pd.testing.assert_frame_equal(before, after)


def test_future_labels_and_label_coverage_are_not_feature_inputs(tmp_path):
    processed, labels, original = prepare(tmp_path)
    table = pd.read_parquet(labels.path)
    table["label_24h"] = 1
    table["scan_coverage_a"] = 123.0
    table["eligible_for_evaluation"] = False
    altered = tmp_path / "altered.parquet"
    table.to_parquet(altered, index=False)
    changed = build_features(processed, replace(labels, path=altered), tmp_path / "features")
    pd.testing.assert_frame_equal(pd.read_parquet(original.path), pd.read_parquet(changed.path))


def test_rolling_start_inclusive_and_snapshot_exclusive(tmp_path):
    processed, labels, _ = prepare(tmp_path, [(T, 5, 97, -20), (T - 1, 5, 97, -50), (T + DAY - 1, 5, 97, -40), (T + DAY, 5, 97, -10)])
    artifact = build_features(processed, labels, tmp_path / "features")
    row = pd.read_parquet(artifact.path).query("timestamp == @T + @DAY and user_min == 5 and user_max == 97").iloc[0]
    assert row.contact_count_1d == 2  # t-24h is included, current t is excluded.
    assert row.rssi_max_7d == -20
    assert row.time_since_last_contact == 1
    assert row.historical_contact_probability == 1


def test_sociopatterns_features_preserve_unknowns(tmp_path):
    source = tmp_path / "HighSchool2013_proximity_net.csv"
    source.write_text(f"0 5 97 MP PC\n{3 * DAY} 5 97 MP PC\n")
    processed = preprocess_contacts(source, "SocioPatterns", tmp_path / "processed")
    labels = build_labels(processed, tmp_path / "labels")
    frame = pd.read_parquet(build_features(processed, labels, tmp_path / "features").path)
    assert frame.rssi_mean_7d.isna().all()
    assert frame.scan_coverage_a.isna().all() and frame.scan_coverage_b.isna().all()
    assert frame.historical_contact_probability.isna().all()


def test_verified_weekday_override_and_disabled_communication_policy(tmp_path):
    processed, labels, _ = prepare(tmp_path)
    with pytest.raises(ValueError, match="可信来源"):
        build_features(processed, labels, tmp_path / "features", weekday_origin=0)
    with pytest.raises(ValueError, match="禁止启用"):
        build_features(processed, labels, tmp_path / "features", communications_enabled=True)
    artifact = build_features(processed, labels, tmp_path / "features", weekday_origin=5, weekday_reference="synthetic fixture convention")
    row = pd.read_parquet(artifact.path).iloc[0]
    assert row.relative_weekday == 5 and row.is_relative_weekend == 1


def test_empty_labels_write_typed_empty_features(tmp_path):
    processed, labels, _ = prepare(tmp_path)
    empty = tmp_path / "empty.parquet"
    schema = pq.ParquetFile(labels.path).schema_arrow
    pq.write_table(pa.Table.from_pylist([], schema=schema), empty)
    artifact = build_features(processed, replace(labels, path=empty), tmp_path / "features")
    assert artifact.report["rows"] == 0 and pd.read_parquet(artifact.path).empty


def test_changed_input_aborts_features_without_publishing_partial_cache(tmp_path, monkeypatch):
    from src import feature_engineering
    processed, labels, _ = prepare(tmp_path)
    original = feature_engineering.parquet_frames
    contacts = processed.directory / "contacts.parquet"
    changed = False

    def mutate_input(path, *args, **kwargs):
        nonlocal changed
        for frame in original(path, *args, **kwargs):
            yield frame
            if path == contacts and not changed:
                stat = contacts.stat()
                os.utime(contacts, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))
                changed = True

    monkeypatch.setattr(feature_engineering, "parquet_frames", mutate_input)
    output = tmp_path / "failed-features"
    with pytest.raises(RuntimeError, match="特征生成期间改变"):
        build_features(processed, labels, output)
    assert not list(output.glob("*.parquet")) and not list(output.glob("*.json"))

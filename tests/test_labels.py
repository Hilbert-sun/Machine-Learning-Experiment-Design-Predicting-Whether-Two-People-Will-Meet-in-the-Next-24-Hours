"""Small synthetic timelines verify the exact future window and candidate/coverage rules."""

import pandas as pd
import pytest
import os

from src.label_builder import build_labels
from src.preprocessing import preprocess_contacts

DAY, T = 86400, 8 * 3600


def prepare(tmp_path, *, events=(), scans=(5, 97), dataset="Copenhagen", duration=3 * DAY):
    if dataset == "Copenhagen":
        path = tmp_path / "bt_symmetric.csv"
        rows = ["timestamp,user_a,user_b,rssi", "0,5,97,-65"]
        rows += [f"{timestamp},{user},-1,0" for timestamp in range(0, duration + 1, 300) for user in scans]
        rows += [f"{timestamp},{a},{b},-70" for timestamp, a, b in events]
    else:
        path = tmp_path / "HighSchool2013_proximity_net.csv"
        rows = ["0 5 97 MP PC", f"{duration} 5 97 MP PC"]
        rows += [f"{timestamp} {a} {b} MP PC" for timestamp, a, b in events]
    path.write_text("\n".join(rows) + "\n")
    return preprocess_contacts(path, dataset, tmp_path / "processed")


@pytest.mark.parametrize("event,expected", [(T, 0), (T + 1, 1), (T + DAY, 1), (T + DAY + 1, 0)])
def test_exact_label_window_boundaries(tmp_path, event, expected):
    processed = prepare(tmp_path, events=[(event, 5, 97)])
    artifact = build_labels(processed, tmp_path / "labels")
    frame = pd.read_parquet(artifact.path)
    row = frame.loc[frame.timestamp.eq(T)].iloc[0]
    assert row.label_24h == expected
    assert row.eligible_for_evaluation and row.scan_coverage_a == row.scan_coverage_b == 1


def test_future_only_pair_and_event_at_snapshot_cannot_create_candidates(tmp_path):
    processed = prepare(tmp_path, events=[(T, 222, 333), (T + 1, 444, 555)])
    frame = pd.read_parquet(build_labels(processed, tmp_path / "labels").path)
    assert frame.loc[frame.timestamp.eq(T), ["user_min", "user_max"]].values.tolist() == [[5, 97]]
    assert set(map(tuple, frame.loc[frame.timestamp.eq(T + DAY), ["user_min", "user_max"]].values)) == {(5, 97), (222, 333), (444, 555)}


@pytest.mark.parametrize("has_contact", [False, True])
def test_low_coverage_never_creates_a_negative_label(tmp_path, has_contact):
    processed = prepare(tmp_path, scans=(5,), events=[(T + 1, 5, 97)] if has_contact else [])
    row = pd.read_parquet(build_labels(processed, tmp_path / "labels").path).iloc[0]
    assert row.label_24h == 1 if has_contact else pd.isna(row.label_24h)
    assert not row.eligible_for_evaluation
    assert row.exclusion_reason == "low_scan_coverage"


def test_sociopatterns_positive_evidence_and_unknown_absence(tmp_path):
    processed = prepare(tmp_path, dataset="SocioPatterns", events=[(T + 1, 5, 97)])
    frame = pd.read_parquet(build_labels(processed, tmp_path / "labels").path)
    assert frame.iloc[0].label_24h == 1
    assert pd.isna(frame.iloc[1].label_24h)
    assert frame.scan_coverage_a.isna().all()
    assert not frame.eligible_for_evaluation.any()


def test_incomplete_horizons_are_excluded_and_cache_reused(tmp_path):
    processed = prepare(tmp_path)
    artifact = build_labels(processed, tmp_path / "labels")
    frame = pd.read_parquet(artifact.path)
    assert (frame.timestamp + DAY <= 3 * DAY).all()
    assert artifact.report["incomplete_snapshots"] > 0
    repeat = build_labels(processed, tmp_path / "labels")
    assert repeat.cached and repeat.path == artifact.path
    assert build_labels(processed, tmp_path / "labels", min_scan_coverage=0.75).path != artifact.path


def test_no_complete_future_window_writes_typed_empty_artifact(tmp_path):
    processed = prepare(tmp_path, duration=3600)
    artifact = build_labels(processed, tmp_path / "labels")
    assert artifact.report["rows"] == 0
    assert pd.read_parquet(artifact.path).empty


@pytest.mark.parametrize("settings", [{"min_scan_coverage": 0}, {"snapshot_hour": 24}, {"horizon_hours": 6}])
def test_invalid_label_policy_rejected(tmp_path, settings):
    with pytest.raises(ValueError):
        build_labels(prepare(tmp_path), tmp_path / "labels", **settings)


def test_changed_input_aborts_labels_without_publishing_partial_cache(tmp_path, monkeypatch):
    from src import label_builder
    processed = prepare(tmp_path)
    original = label_builder.parquet_frames
    observations = processed.directory / "observations.parquet"
    changed = False

    def mutate_input(path, *args, **kwargs):
        nonlocal changed
        for frame in original(path, *args, **kwargs):
            yield frame
            if path == observations and not changed:
                stat = observations.stat()
                os.utime(observations, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))
                changed = True

    monkeypatch.setattr(label_builder, "parquet_frames", mutate_input)
    output = tmp_path / "failed-labels"
    with pytest.raises(RuntimeError, match="标签生成期间改变"):
        build_labels(processed, output)
    assert not list(output.glob("*.parquet")) and not list(output.glob("*.json"))

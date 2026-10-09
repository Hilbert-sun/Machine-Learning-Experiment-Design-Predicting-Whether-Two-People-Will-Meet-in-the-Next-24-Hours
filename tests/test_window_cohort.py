import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.label_builder import build_labels
from src.preprocessing import ProcessedDataset, CONTACT_SCHEMA, OBSERVATION_SCHEMA
from src.window_cohort import build_comparison_cohort, past_pairs, row_hash, split_support

DAY = 86400


def fixture_processed(tmp_path, *, coverage=True):
    directory = tmp_path / "processed"
    directory.mkdir()
    contacts = [{"timestamp": day*DAY + 100, "source_timestamp": day*DAY+100, "user_min": a, "user_max": b, "rssi": -70.0}
                for day in range(28) for a, b in ((1, 2), (2, 3))]
    contacts += [{"timestamp": 20*DAY, "source_timestamp": 20*DAY, "user_min": 1, "user_max": 9, "rssi": -50.0}]
    pq.write_table(pa.Table.from_pylist(sorted(contacts, key=lambda x: x["timestamp"]), schema=CONTACT_SCHEMA), directory / "contacts.parquet")
    observations = [{"timestamp": t, "user_id": user, "scan_observed": True if coverage else None}
                    for t in range(0, 28*DAY, 300) for user in (1, 2, 3, 9)]
    pq.write_table(pa.Table.from_pylist(observations, schema=OBSERVATION_SCHEMA), directory / "observations.parquet")
    return ProcessedDataset(directory, {"dataset": "Copenhagen", "scan_coverage_available": coverage,
                            "source_timestamp_min": 0, "source_timestamp_max": 28*DAY-300, "time_origin_seconds": 0}, False)


def test_candidates_are_past_only_and_common_span_and_hashes_hold(tmp_path):
    processed = fixture_processed(tmp_path)
    labels = build_labels(processed, tmp_path / "labels")
    artifact, manifest = build_comparison_cohort(processed, labels, tmp_path / "cohort")
    frame = pd.read_parquet(artifact.path)
    assert frame.timestamp.min() >= 7*DAY
    assert frame.timestamp.max() + DAY <= processed.report["source_timestamp_max"]
    assert not frame.loc[frame.timestamp.lt(20*DAY)].user_max.eq(9).any()
    for t, group in frame.groupby("timestamp"):
        allowed = set(past_pairs(processed, t, 1).itertuples(index=False, name=None))
        assert set(group[["user_min", "user_max"]].itertuples(index=False, name=None)) <= allowed
    assert row_hash(frame, labels=True) == manifest["label_hash"]
    assert frame.sample_key.is_unique
    repeated, other = build_comparison_cohort(processed, labels, tmp_path / "cohort")
    assert repeated.cached and other == manifest
    assert manifest["support"]["status"] == "insufficient_days"  # Too few class samples, not fake negatives.


def test_unknown_observation_never_generates_reliable_negatives(tmp_path):
    processed = fixture_processed(tmp_path, coverage=False)
    artifact, manifest = build_comparison_cohort(processed, build_labels(processed, tmp_path / "labels"), tmp_path / "cohort")
    assert pd.read_parquet(artifact.path).empty
    assert manifest["support"]["status"] == "insufficient_days"
    assert sum(d["excluded_coverage_or_unknown"] for d in manifest["daily_filter_funnel"]) > 0


def test_twenty_day_support_preserves_purge_and_disables_impossible_calibration():
    frame = pd.DataFrame([{"dataset_id": "copenhagen", "timestamp": d*DAY+28800, "user_min": 1, "user_max": i+2,
                           "label_24h": i%2} for d in range(7, 27) for i in range(60)])
    split, support = split_support(frame)
    assert support["status"] == "ready"
    assert [s["distinct_prediction_days"] for s in support["sets"].values()] == [11, 3, 4]
    assert split.train.timestamp.max()+DAY < split.validation.timestamp.min()
    assert split.validation.timestamp.max()+DAY < split.test.timestamp.min()
    assert support["calibration"]["method"] is None

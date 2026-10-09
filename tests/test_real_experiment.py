"""T17 safeguards: meaningfully sized cohorts, chronological feasibility and scale parity."""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.feature_engineering import build_features
from src.pipeline_cache import PipelineArtifact
from src.preprocessing import preprocess_contacts
from src.real_experiment import feasibility_reasons, snapshot_capacity
from src.temporal_split import chronological_split
from test_leakage import synthetic_frame


def test_scaled_history_aggregation_preserves_bins_days_and_rssi_across_row_groups(tmp_path):
    source = tmp_path / "bt_symmetric.csv"
    source.write_text("timestamp,user_a,user_b,rssi\n0,5,97,-80\n100,5,97,-70\n300,97,222,-60\n86400,5,97,-50\n86500,5,97,-40\n172800,5,-1,0\n")
    keys_path = tmp_path / "keys.parquet"
    pq.write_table(pa.Table.from_pylist([{"timestamp": 86700, "user_min": 5, "user_max": 97}], schema=pa.schema([("timestamp", pa.int64()), ("user_min", pa.int64()), ("user_max", pa.int64())])), keys_path)
    keys = PipelineArtifact(keys_path, {"policy": {"min_scan_coverage": 0.5}}, False)
    outputs = []
    for size in (1, 100):
        processed = preprocess_contacts(source, "Copenhagen", tmp_path / f"processed-{size}", chunksize=size)
        artifact = build_features(processed, keys, tmp_path / f"features-{size}")
        outputs.append(pd.read_parquet(artifact.path))
    pd.testing.assert_frame_equal(outputs[0], outputs[1])
    row = outputs[0].iloc[0]
    assert row.contact_count_1d == 2 and row.contact_count_7d == 4
    assert row.contact_bins_7d == 2 and row.unique_contact_days_7d == 2
    assert row.rssi_mean_7d == -60 and row.rssi_max_7d == -40


def test_short_real_timeline_cannot_be_repaired_by_more_overlapping_snapshots():
    capacities = [snapshot_capacity(39620, 403180, hours) for hours in (24, 6, 1)]
    assert [row["complete_snapshots"] for row in capacities] == [3, 13, 76]
    assert all(row["purged_time_groups"]["validation"] == 0 for row in capacities)


def test_meaningfulness_gate_checks_both_classes_and_time_groups_before_fitting():
    small = chronological_split(synthetic_frame())
    assert any("200" in reason for reason in feasibility_reasons(small))
    large = pd.concat([synthetic_frame().assign(user_max=lambda frame: frame.user_max + offset * 100) for offset in range(3)], ignore_index=True)
    split = chronological_split(large)
    assert feasibility_reasons(split) == []
    split.test["label_24h"] = 0
    assert any(reason.startswith("test:") for reason in feasibility_reasons(split))

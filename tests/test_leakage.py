"""Synthetic sample keys verify chronological grouping and inclusive-horizon purging."""

from pathlib import Path

import pandas as pd
import pytest

from src.feature_engineering import FEATURE_NAMES
from src.pipeline_cache import PipelineArtifact
from src.temporal_split import TrainingDataError, chronological_split, prepare_cohort, validation_partition

DAY = 86400


def synthetic_frame(days=40):
    rows = []
    for day in range(days):
        for pair in range(4):
            row = {name: None for name in FEATURE_NAMES}
            row.update(timestamp=day * DAY + 28800, user_min=5, user_max=97 + pair, label_24h=pair % 2,
                       contact_count_1d=float(pair), contact_count_7d=float(pair + day % 3),
                       historical_contact_probability=0.15 if pair % 2 == 0 else 0.85,
                       time_since_last_contact=float((pair + 1) * 3600), prediction_hour=8.0,
                       prediction_day_index=float(day), scan_coverage_a=1.0, scan_coverage_b=1.0)
            rows.append(row)
    return pd.DataFrame(rows)


def artifacts(tmp_path, frame):
    labels = frame[["timestamp", "user_min", "user_max", "label_24h"]].copy()
    labels["eligible_for_evaluation"] = True
    features = frame.drop(columns="label_24h")
    lp, fp = tmp_path / "labels.parquet", tmp_path / "features.parquet"
    labels.to_parquet(lp, index=False)
    features.to_parquet(fp, index=False)
    return PipelineArtifact(lp, {"policy": {"horizon_hours": 24}}, False), PipelineArtifact(fp, {}, False)


def test_grouped_chronological_split_purges_equal_boundary_and_preserves_test():
    frame = synthetic_frame(10).sample(frac=1, random_state=7)
    split = chronological_split(frame)
    assert split.train.timestamp.max() + DAY < split.validation.timestamp.min()
    assert split.validation.timestamp.max() + DAY < split.test.timestamp.min()
    assert split.report["purged_rows"] == 8
    assert len(split.test) == 8
    all_times = [set(part.timestamp) for part in (split.train, split.validation, split.test)]
    assert not any(all_times[i] & all_times[j] for i in range(3) for j in range(i + 1, 3))
    assert all(part.groupby("timestamp").size().eq(4).all() for part in (split.train, split.validation, split.test))


def test_cohort_excludes_unknown_and_low_coverage_without_imputing_targets(tmp_path):
    labels, features = artifacts(tmp_path, synthetic_frame(10))
    table = pd.read_parquet(labels.path)
    table.loc[0, "eligible_for_evaluation"] = False
    table.loc[1, "label_24h"] = None
    table.to_parquet(labels.path, index=False)
    cohort = prepare_cohort(labels, features)
    assert len(cohort) == 38 and cohort.attrs["excluded_rows"] == 2
    assert "eligible_for_evaluation" not in cohort


def test_bad_feature_schema_duplicate_and_mismatched_keys_rejected(tmp_path):
    labels, features = artifacts(tmp_path, synthetic_frame(10))
    table = pd.read_parquet(features.path)
    table["future_scan_coverage"] = 1.0
    table.to_parquet(features.path, index=False)
    with pytest.raises(TrainingDataError, match="白名单"):
        prepare_cohort(labels, features)
    table = table.drop(columns="future_scan_coverage").iloc[1:]
    table.to_parquet(features.path, index=False)
    with pytest.raises(TrainingDataError, match="不完全一致"):
        prepare_cohort(labels, features)
    pd.concat([table, table.iloc[:1]]).to_parquet(features.path, index=False)
    with pytest.raises(TrainingDataError, match="重复"):
        prepare_cohort(labels, features)


def test_zero_eligible_cohort_refused(tmp_path):
    labels, features = artifacts(tmp_path, synthetic_frame(10))
    table = pd.read_parquet(labels.path)
    table["eligible_for_evaluation"] = False
    table.to_parquet(labels.path, index=False)
    with pytest.raises(TrainingDataError, match="没有覆盖策略"):
        prepare_cohort(labels, features)


def test_calibration_and_tuning_are_purged_and_separate():
    split = chronological_split(synthetic_frame())
    calibration, tuning = validation_partition(split.validation)
    assert calibration.timestamp.max() + DAY < tuning.timestamp.min()
    assert set(calibration.timestamp).isdisjoint(tuning.timestamp)


@pytest.mark.parametrize("days", [1, 2, 3])
def test_too_short_timeline_is_not_repaired_with_random_split(days):
    with pytest.raises(TrainingDataError):
        chronological_split(synthetic_frame(days))

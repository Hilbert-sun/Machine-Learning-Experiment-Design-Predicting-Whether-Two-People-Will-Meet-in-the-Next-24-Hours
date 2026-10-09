"""T19 common cohort: one-day candidates, seven-day span, unchanged 24h labels."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

from src.baseline_audit import immutable_json, sha256
from src.pipeline_cache import cache_artifact, parquet_frames
from src.temporal_split import TrainingDataError, chronological_split, validation_partition

DAY = 86400
COHORT_VERSION = 1
KEYS = ["dataset_id", "timestamp", "user_min", "user_max"]


def row_hash(frame, *, labels=False):
    columns = KEYS + (["label_24h"] if labels else [])
    payload = frame.sort_values(KEYS).loc[:, columns].to_csv(index=False, float_format="%.0f").encode()
    return hashlib.sha256(payload).hexdigest()


def past_pairs(processed, t, days):
    expression = (ds.field("timestamp") >= t-days*DAY) & (ds.field("timestamp") < t)
    pairs = set()
    for frame in parquet_frames(processed.directory / "contacts.parquet", ["user_min", "user_max"], expression):
        pairs.update(frame.drop_duplicates().itertuples(index=False, name=None))
    return pd.DataFrame(sorted(pairs), columns=["user_min", "user_max"], dtype="int64")


def part_summary(part):
    return {"rows": len(part), "positive": int(part.label_24h.eq(1).sum()), "negative": int(part.label_24h.eq(0).sum()),
            "prediction_times": sorted(int(t) for t in part.timestamp.unique()), "distinct_prediction_days": int(part.timestamp.nunique()),
            "sample_key_hash": row_hash(part), "label_hash": row_hash(part, labels=True)}


def split_support(frame):
    try:
        split = chronological_split(frame)
    except TrainingDataError as exc:
        return None, {"status": "insufficient_days", "reason": str(exc),
                      "alternative": "Prespecify forward chronological train/validation/future-test folds or acquire a longer source; never randomly split rows."}
    sets = {name: part_summary(getattr(split, name)) for name in ("train", "validation", "test")}
    if any(s["distinct_prediction_days"] < 2 or min(s["positive"], s["negative"]) < 20 for s in sets.values()):
        return None, {"status": "insufficient_days", "sets": sets, "reason": "Need >=2 dates and >=20 observations of each class per set."}
    try:
        early, later = validation_partition(split.validation)
        supported = min(early.label_24h.value_counts().reindex([0, 1], fill_value=0)) >= 20 and later.timestamp.nunique() >= 2
        calibration = {"method": "sigmoid" if supported else None, "fit": part_summary(early), "tuning": part_summary(later),
                       "reason": "Prespecified support gate" if supported else "Insufficient independent validation support; use raw models."}
    except TrainingDataError as exc:
        calibration = {"method": None, "reason": str(exc), "tuning": part_summary(split.validation)}
    return split, {"status": "ready", "sets": sets, "temporal_split": split.report, "calibration": calibration}


def build_comparison_cohort(processed, labels, output, *, dataset_id="copenhagen"):
    if not dataset_id or "|" in dataset_id:
        raise ValueError("dataset_id must be a nonempty namespace without '|'.")
    output = Path(output)
    paths = [processed.directory / "contacts.parquet", processed.directory / "observations.parquet", labels.path]
    signatures = {str(path.resolve()): sha256(path) for path in paths}
    identity = {"cohort_version": COHORT_VERSION, "dataset_id": dataset_id, "inputs": signatures,
                "candidate_days": 1, "common_history_days": 7, "label_policy": labels.report["policy"]}
    schema = pa.schema([("dataset_id", pa.string()), ("sample_key", pa.string()), ("timestamp", pa.int64()),
                        ("user_min", pa.int64()), ("user_max", pa.int64()), ("label_24h", pa.int8()),
                        ("future_scan_coverage_a", pa.float64()), ("future_scan_coverage_b", pa.float64())])

    def produce(writer):
        rows, per_day = 0, []
        start = processed.report["source_timestamp_min"] - processed.report["time_origin_seconds"]
        end = processed.report["source_timestamp_max"] - processed.report["time_origin_seconds"]
        old = pd.read_parquet(labels.path)
        if old.duplicated(["timestamp", "user_min", "user_max"]).any():
            raise TrainingDataError("Duplicate original label keys.")
        for t in labels.report["snapshot_times"]:
            day = old.loc[old.timestamp.eq(t)]
            span = t-7*DAY >= start and t+DAY <= end
            entry = {"timestamp": int(t), "study_day": int(t//DAY+1), "all_past_candidate_rows": len(day),
                     "excluded_incomplete_7d_span": len(day) if not span else 0,
                     "one_day_candidates": 0, "excluded_not_1d_candidate": 0, "excluded_coverage_or_unknown": 0,
                     "eligible_rows": 0, "positive": 0, "negative": 0}
            if span:
                pairs = past_pairs(processed, t, 1)
                selected = pairs.merge(day, on=["user_min", "user_max"], how="left", validate="one_to_one", indicator=True)
                if not selected._merge.eq("both").all():
                    raise TrainingDataError("Historical one-day pair missing original labels.")
                eligible = selected.loc[selected.eligible_for_evaluation.eq(True) & selected.label_24h.notna()].copy()
                entry.update(one_day_candidates=len(selected), excluded_not_1d_candidate=len(day)-len(selected),
                             excluded_coverage_or_unknown=len(selected)-len(eligible), eligible_rows=len(eligible),
                             positive=int(eligible.label_24h.eq(1).sum()), negative=int(eligible.label_24h.eq(0).sum()))
                eligible["dataset_id"] = dataset_id
                eligible["sample_key"] = [f"{dataset_id}|{int(t)}|{int(a)}|{int(b)}" for a, b in eligible[["user_min", "user_max"]].itertuples(index=False, name=None)]
                eligible = eligible.rename(columns={"scan_coverage_a": "future_scan_coverage_a", "scan_coverage_b": "future_scan_coverage_b"})
                writer.write_table(pa.Table.from_pandas(eligible.loc[:, schema.names], schema=schema, preserve_index=False))
                rows += len(eligible)
            per_day.append(entry)
        if {str(p.resolve()): sha256(p) for p in paths} != signatures:
            raise RuntimeError("Cohort inputs changed during construction.")
        return {"rows": rows, "per_day": per_day, "source_start": start, "source_end": end}

    artifact = cache_artifact(output, "cohort", identity, schema, produce)
    frame = pd.read_parquet(artifact.path)
    frame.attrs.update(source_rows=len(frame), excluded_rows=0)
    split, support = split_support(frame)
    assignments = frame.copy()
    assignments["split"] = "purged"
    if split is not None:
        r = split.report
        assignments.loc[(frame.timestamp < r["validation_start"]) & (frame.timestamp+DAY < r["validation_start"]), "split"] = "train"
        assignments.loc[(frame.timestamp >= r["validation_start"]) & (frame.timestamp < r["test_start"]) & (frame.timestamp+DAY < r["test_start"]), "split"] = "validation"
        assignments.loc[frame.timestamp >= r["test_start"], "split"] = "test"
    assignment_path = artifact.path.with_name(artifact.path.stem + "-splits.parquet")
    if not assignment_path.exists():
        assignments.to_parquet(assignment_path, index=False)
    else:
        pd.testing.assert_frame_equal(pd.read_parquet(assignment_path), assignments)
    manifest = {"cohort_version": COHORT_VERSION, "dataset_id": dataset_id, "candidate_interval": "[t-1d,t)",
                "history_completeness": "t-7d >= source_start; time span is not proof of continuous scans",
                "label_interval": "(t,t+24h]", "coverage_threshold": labels.report["policy"]["min_scan_coverage"],
                "shared_windows": [1, 3, 7], "rows": len(frame), "sample_key_hash": row_hash(frame), "label_hash": row_hash(frame, labels=True),
                "cohort_filename": artifact.path.name, "cohort_sha256": sha256(artifact.path),
                "split_filename": assignment_path.name, "split_sha256": sha256(assignment_path),
                "source_hashes": {p.name: sha256(p) for p in paths}, "daily_filter_funnel": artifact.report["per_day"],
                "support": support, "purged_by_day": [{"timestamp": int(t), "rows": len(g), "positive": int(g.label_24h.eq(1).sum()),
                                                       "negative": int(g.label_24h.eq(0).sum())} for t, g in assignments.loc[assignments.split.eq("purged")].groupby("timestamp")]}
    immutable_json(output / "T19_COHORT_MANIFEST.json", manifest)
    return artifact, manifest

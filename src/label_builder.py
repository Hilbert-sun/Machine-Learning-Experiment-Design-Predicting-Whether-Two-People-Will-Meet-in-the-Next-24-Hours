"""Known-pair daily snapshots with exact 24-hour labels and conservative missingness."""

from collections import Counter
from itertools import islice

import pyarrow as pa
import pyarrow.dataset as ds

from src.pipeline_cache import cache_artifact, file_signatures, parquet_frames

DAY = 86400
VERSION = 1
LABEL_SCHEMA = pa.schema([
    ("timestamp", pa.int64()), ("user_min", pa.int64()), ("user_max", pa.int64()),
    ("label_24h", pa.int8()), ("scan_coverage_a", pa.float64()), ("scan_coverage_b", pa.float64()),
    ("eligible_for_evaluation", pa.bool_()), ("exclusion_reason", pa.string()),
])


def build_labels(processed, output, *, snapshot_hour=8, horizon_hours=24, min_scan_coverage=0.5):
    """Positive evidence is retained; absent events require sufficient scans to be 0.

    Unknown/low coverage excludes even observed positives from the primary
    evaluation cohort. Incomplete future horizons produce no samples. No negative
    downsampling, random splits or future-informed candidate construction occurs.
    """
    if type(snapshot_hour) is not int or not 0 <= snapshot_hour < 24 or horizon_hours != 24:
        raise ValueError("首版只支持每日一次、有效整数小时和24小时预测窗口。")
    if not 0 < min_scan_coverage <= 1:
        raise ValueError("最低扫描覆盖率必须在 (0, 1]。")
    contacts, observations = processed.directory / "contacts.parquet", processed.directory / "observations.parquet"
    signatures = file_signatures([contacts, observations])
    policy = {"snapshot_hour": snapshot_hour, "horizon_hours": 24, "min_scan_coverage": min_scan_coverage, "candidate_mode": "Known Pair"}
    identity = {"version": VERSION, "inputs": signatures, "policy": policy, "source_report": processed.report}

    def produce(writer):
        origin = processed.report["time_origin_seconds"]
        start = processed.report["source_timestamp_min"] - origin
        end = processed.report["source_timestamp_max"] - origin
        snapshots = [day * DAY + snapshot_hour * 3600 for day in range(start // DAY, end // DAY + 1)]
        candidates, previous = set(), None
        counts = Counter()
        snapshot_times = []
        for t in snapshots:
            if t < start or t + DAY > end:
                counts["incomplete_snapshots"] += 1
                continue
            past = ds.field("timestamp") < t
            if previous is not None:
                past &= ds.field("timestamp") >= previous
            for frame in parquet_frames(contacts, ["user_min", "user_max"], past):
                candidates.update(frame.drop_duplicates().itertuples(index=False, name=None))
            previous = t
            positive = set()
            future = (ds.field("timestamp") > t) & (ds.field("timestamp") <= t + DAY)
            for frame in parquet_frames(contacts, ["user_min", "user_max"], future):
                positive.update(frame.drop_duplicates().itertuples(index=False, name=None))
            scan_counts = Counter()
            if processed.report["scan_coverage_available"]:
                for frame in parquet_frames(observations, ["user_id", "scan_observed"], future):
                    scan_counts.update(frame.loc[frame.scan_observed.eq(True), "user_id"].value_counts().to_dict())
            snapshot_times.append(t)
            iterator = iter(sorted(candidates))
            while batch := list(islice(iterator, 10_000)):
                records = []
                for a, b in batch:
                    ca = scan_counts[a] / 288 if processed.report["scan_coverage_available"] else None
                    cb = scan_counts[b] / 288 if processed.report["scan_coverage_available"] else None
                    eligible = ca is not None and cb is not None and min(ca, cb) >= min_scan_coverage
                    label = 1 if (a, b) in positive else 0 if eligible else None
                    reason = None if eligible else "scan_coverage_unknown" if ca is None else "low_scan_coverage"
                    records.append({"timestamp": t, "user_min": int(a), "user_max": int(b), "label_24h": label,
                                    "scan_coverage_a": ca, "scan_coverage_b": cb, "eligible_for_evaluation": eligible, "exclusion_reason": reason})
                    counts["rows"] += 1
                    counts["eligible_samples"] += int(eligible)
                    counts["positive_labels" if label == 1 else "negative_labels" if label == 0 else "unknown_labels"] += 1
                writer.write_table(pa.Table.from_pylist(records, schema=LABEL_SCHEMA))
        if file_signatures([contacts, observations]) != signatures:
            raise RuntimeError("输入在标签生成期间改变，未发布缓存。")
        return {"rows": counts["rows"], "eligible_samples": counts["eligible_samples"], "positive_labels": counts["positive_labels"],
                "negative_labels": counts["negative_labels"], "unknown_labels": counts["unknown_labels"],
                "incomplete_snapshots": counts["incomplete_snapshots"], "snapshot_times": snapshot_times, "policy": policy,
                "dataset": processed.report["dataset"], "time_origin_seconds": origin,
                "label_interval": "(t, t + 24h]", "candidate_interval": "timestamp < t",
                "coverage_interval": "scan-bin timestamp in (t, t + 24h]; 288 expected bins per reporter",
                "unknown_policy": "Observed positives remain 1; unknown/low-coverage rows are excluded from primary evaluation; absent events without sufficient scans stay null."}

    return cache_artifact(output, "labels", identity, LABEL_SCHEMA, produce)

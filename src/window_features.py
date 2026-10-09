"""T20 explicit bounded-history features; legacy T17 feature contracts are untouched."""

from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from src.baseline_audit import sha256
from src.pipeline_cache import cache_artifact, parquet_frames
from src.window_cohort import DAY, KEYS, row_hash, COHORT_VERSION

FEATURE_VERSION = 1
WINDOW_FEATURES = ("pair_contact_count", "pair_contact_bins", "pair_contact_days", "recency_seconds",
                   "rssi_mean", "rssi_max", "participant_a_activity", "participant_b_activity",
                   "common_neighbors", "network_degree_a", "network_degree_b",
                   "scan_coverage_a", "scan_coverage_b", "historical_contact_probability", "observed_history_days")
SCHEMA = pa.schema([("dataset_id", pa.string()), ("timestamp", pa.int64()), ("user_min", pa.int64()), ("user_max", pa.int64()),
                    *((name, pa.float64()) for name in WINDOW_FEATURES)])


def bounded_context(processed, t, days):
    stats = {name: Counter() for name in ("count", "bins", "days", "rssi_sum", "rssi_n")}
    last, rssi_max, previous_bins, previous_days = {}, {}, {}, {}
    neighbors, buckets, activity, scans = defaultdict(set), defaultdict(set), Counter(), Counter()
    condition = (ds.field("timestamp") >= t-days*DAY) & (ds.field("timestamp") < t)
    bin_size = 300 if processed.report["dataset"] == "Copenhagen" else 20
    for frame in parquet_frames(processed.directory / "contacts.parquet", ["timestamp", "user_min", "user_max", "rssi"], condition):
        keys = ["user_min", "user_max"]
        grouped = frame.groupby(keys, sort=False)
        stats["count"].update(grouped.size().to_dict())
        signal = grouped.rssi.agg(["sum", "count", "max"])
        stats["rssi_sum"].update(signal["sum"].to_dict())
        stats["rssi_n"].update(signal["count"].to_dict())
        for pair, value in signal["max"].dropna().items():
            rssi_max[pair] = max(rssi_max.get(pair, -np.inf), float(value))
        for pair, value in grouped.timestamp.max().items():
            last[pair] = max(last.get(pair, -1), int(value))
        for column, divisor, previous, destination in (("bin", bin_size, previous_bins, stats["bins"]), ("day", DAY, previous_days, stats["days"])):
            unique = frame[keys].assign(**{column: frame.timestamp.to_numpy()//divisor}).drop_duplicates(keys+[column])
            if previous:
                prior = pd.DataFrame([(a, b, value) for (a, b), value in previous.items()], columns=keys+["previous"])
                compared = unique.merge(prior, on=keys, how="left")
                fresh = compared.loc[compared[column].gt(compared.previous.fillna(-1))]
            else:
                fresh = unique
            destination.update(fresh.groupby(keys, sort=False).size().to_dict())
            previous.update(unique.groupby(keys, sort=False)[column].max().to_dict())
        for a, b in signal.index:
            neighbors[a].add(b)
            neighbors[b].add(a)
        activity.update(frame.user_min.value_counts().to_dict())
        activity.update(frame.user_max.value_counts().to_dict())
        daily = frame[keys].assign(bucket=(t-1-frame.timestamp.to_numpy())//DAY).drop_duplicates(keys+["bucket"])
        for a, b, bucket in daily.itertuples(index=False, name=None):
            buckets[(a, b)].add(int(bucket))
    if processed.report["scan_coverage_available"]:
        for frame in parquet_frames(processed.directory / "observations.parquet", ["timestamp", "user_id", "scan_observed"], condition):
            frame = frame.loc[frame.scan_observed.eq(True)].copy()
            frame["bucket"] = (t-1-frame.timestamp)//DAY
            scans.update(frame.groupby(["user_id", "bucket"]).size().to_dict())
    return stats, last, rssi_max, neighbors, buckets, activity, scans


def snapshot_features(processed, keys, t, days, threshold):
    stats, last, rssi_max, neighbors, positive_buckets, activity, scans = bounded_context(processed, t, days)
    records = []
    for dataset_id, _, a, b in keys.loc[:, KEYS].itertuples(index=False, name=None):
        pair = (a, b)
        observed = {bucket for bucket in range(days) if min(scans[(a, bucket)], scans[(b, bucket)])/288 >= threshold}
        available = processed.report["scan_coverage_available"]
        n = stats["rssi_n"][pair]
        records.append({"dataset_id": dataset_id, "timestamp": int(t), "user_min": int(a), "user_max": int(b),
                        "pair_contact_count": stats["count"][pair], "pair_contact_bins": stats["bins"][pair], "pair_contact_days": stats["days"][pair],
                        "recency_seconds": t-last[pair] if pair in last else None,
                        "rssi_mean": stats["rssi_sum"][pair]/n if n else None, "rssi_max": rssi_max.get(pair),
                        "participant_a_activity": activity[a], "participant_b_activity": activity[b],
                        "common_neighbors": len(neighbors[a]&neighbors[b]), "network_degree_a": len(neighbors[a]), "network_degree_b": len(neighbors[b]),
                        "scan_coverage_a": sum(scans[(a, bucket)] for bucket in range(days))/(days*288) if available else None,
                        "scan_coverage_b": sum(scans[(b, bucket)] for bucket in range(days))/(days*288) if available else None,
                        "historical_contact_probability": len(positive_buckets[pair]&observed)/len(observed) if observed else None,
                        "observed_history_days": len(observed) if available else None})
    return pa.Table.from_pylist(records, schema=SCHEMA)


def build_window_features(processed, cohort, output, *, history_window_days, min_scan_coverage=0.5, progress=None):
    if history_window_days not in (1, 3, 7):
        raise ValueError("Research windows must be1/3/7 days.")
    if not 0 < min_scan_coverage <= 1:
        raise ValueError("Coverage must be in (0,1].")
    output = Path(output)
    keys = pd.read_parquet(cohort.path, columns=KEYS).sort_values(KEYS).reset_index(drop=True)
    if keys.duplicated(KEYS).any() or keys.dataset_id.nunique() > 1 or (keys.user_min < 0).any() or (keys.user_min >= keys.user_max).any():
        raise ValueError("Feature keys must be unique, canonical and isolated to one dataset.")
    start = processed.report["source_timestamp_min"] - processed.report["time_origin_seconds"]
    if len(keys) and (keys.timestamp-7*DAY < start).any():
        raise ValueError("Common cohort lacks full7d source span.")
    sources = {name: sha256(processed.directory/name) for name in ("contacts.parquet", "observations.parquet")}
    identity = {"feature_version": FEATURE_VERSION, "cohort_version": COHORT_VERSION, "key_hash": row_hash(keys),
                "source_hashes": sources, "dataset": processed.report["dataset"], "coverage_available": processed.report["scan_coverage_available"],
                "source_start": start, "history_window_days": history_window_days, "min_scan_coverage": min_scan_coverage}

    def produce(writer):
        total = 0
        for t, group in keys.groupby("timestamp", sort=True):
            # Each snapshot is committed independently: restart reuses completed chunks.
            daily_identity = {**identity, "timestamp": int(t), "key_hash": row_hash(group)}
            def daily(daily_writer):
                table = snapshot_features(processed, group, int(t), history_window_days, min_scan_coverage)
                daily_writer.write_table(table)
                return {"rows": len(table)}
            chunk = cache_artifact(output/"snapshots", f"{history_window_days}d", daily_identity, SCHEMA, daily)
            writer.write_table(pq.read_table(chunk.path, schema=SCHEMA))
            total += len(group)
            if progress:
                progress(int(t), total, chunk.cached)
        if {name: sha256(processed.directory/name) for name in sources} != sources:
            raise RuntimeError("Feature sources changed during calculation.")
        return {"rows": total, "history_window_days": history_window_days, "feature_version": FEATURE_VERSION,
                "cohort_version": COHORT_VERSION, "feature_columns": list(WINDOW_FEATURES), "key_hash": row_hash(keys),
                "interval": "[t-window,t)", "source_hashes": sources, "future_fields_included": False,
                "frequency_definition": "contact-positive rolling24h buckets / sufficiently scanned buckets within this window; null if none",
                "cache": "content signatures plus window/version/cohort; resumable snapshot Parquet chunks; atomic publication"}
    return cache_artifact(output, f"bounded-{history_window_days}d", identity, SCHEMA, produce)

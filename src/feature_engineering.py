"""Strictly historical contact, network and observation features for T07 keys."""

from collections import Counter, defaultdict

import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds

from src.pipeline_cache import cache_artifact, file_signatures, parquet_frames

DAY = 86400
VERSION = 1
WINDOWS = (1, 3, 7, 14)
FEATURE_NAMES = (
    *(f"contact_count_{window}d" for window in WINDOWS), "contact_bins_1d", "contact_bins_7d",
    "time_since_last_contact", "unique_contact_days_7d", "unique_contact_days_14d",
    "historical_contact_probability", "rssi_mean_7d", "rssi_max_7d", "sms_count_7d", "call_count_7d",
    "prediction_day_index", "prediction_hour", "relative_weekday", "is_relative_weekend",
    "participant_a_activity_7d", "participant_b_activity_7d", "common_neighbors_historical",
    "historical_network_degree_a", "historical_network_degree_b", "scan_coverage_a", "scan_coverage_b",
    *(f"history_complete_{window}d" for window in WINDOWS),
)
FEATURE_SCHEMA = pa.schema([
    ("timestamp", pa.int64()), ("user_min", pa.int64()), ("user_max", pa.int64()),
    *((name, pa.float64()) for name in FEATURE_NAMES),
])


def _history_context(processed, t):
    """Aggregate sorted Parquet chunks; per-pair last-bin/day prevents chunk duplicates."""
    contacts = processed.directory / "contacts.parquet"
    bin_size = 300 if processed.report["dataset"] == "Copenhagen" else 20
    result = {}
    neighbors, activity, positive_buckets = defaultdict(set), Counter(), defaultdict(set)
    for window in WINDOWS:
        stats = {name: Counter() for name in ("count", "bins", "days", "rssi_sum", "rssi_n")}
        stats["rssi_max"] = {}
        last_bin, last_day = {}, {}
        expression = (ds.field("timestamp") >= t - window * DAY) & (ds.field("timestamp") < t)
        for frame in parquet_frames(contacts, ["timestamp", "user_min", "user_max", "rssi"], expression):
            for pair, group in frame.groupby(["user_min", "user_max"]):
                stats["count"][pair] += len(group)
                bins = np.unique(group.timestamp.to_numpy() // bin_size)
                days = np.unique(group.timestamp.to_numpy() // DAY)
                stats["bins"][pair] += int((bins > last_bin.get(pair, -1)).sum())
                stats["days"][pair] += int((days > last_day.get(pair, -1)).sum())
                last_bin[pair], last_day[pair] = int(bins[-1]), int(days[-1])
                if window == 7:
                    signal = group.rssi.dropna()
                    stats["rssi_sum"][pair] += float(signal.sum())
                    stats["rssi_n"][pair] += len(signal)
                    if len(signal):
                        stats["rssi_max"][pair] = max(stats["rssi_max"].get(pair, -np.inf), float(signal.max()))
                    a, b = pair
                    neighbors[a].add(b)
                    neighbors[b].add(a)
                    activity[a] += len(group)
                    activity[b] += len(group)
                if window == 14:
                    positive_buckets[pair].update((t - 1 - group.timestamp.to_numpy()) // DAY)
        result[window] = stats
    scans = Counter()
    if processed.report["scan_coverage_available"]:
        expression = (ds.field("timestamp") >= t - 14 * DAY) & (ds.field("timestamp") < t)
        for frame in parquet_frames(processed.directory / "observations.parquet", ["timestamp", "user_id", "scan_observed"], expression):
            frame = frame.loc[frame.scan_observed.eq(True)].copy()
            frame["bucket"] = (t - 1 - frame.timestamp) // DAY
            scans.update(frame.groupby(["user_id", "bucket"]).size().to_dict())
    return result, neighbors, activity, positive_buckets, scans


def build_features(processed, labels, output, *, weekday_origin=None, weekday_reference=None, communications_enabled=False):
    """Read only label keys, never labels or future eligibility/coverage columns.

    Weekday indexing requires an explicitly supplied, documented source convention.
    Communication features remain null until reliable availability is implemented.
    """
    if communications_enabled:
        raise ValueError("通讯可用时间未验证，初版禁止启用电话/短信特征。")
    if weekday_origin is not None and (type(weekday_origin) is not int or not 0 <= weekday_origin < 7 or not weekday_reference):
        raise ValueError("星期原点必须为0–6并附有可信来源说明。")
    paths = [processed.directory / "contacts.parquet", processed.directory / "observations.parquet", labels.path]
    signatures = file_signatures(paths)
    identity = {"version": VERSION, "inputs": signatures, "weekday_origin": weekday_origin,
                "weekday_reference": weekday_reference, "label_policy": labels.report["policy"], "source_report": processed.report}
    threshold = labels.report["policy"]["min_scan_coverage"]

    def produce(writer):
        last_t, context, previous = None, None, None
        last_contact = {}
        count = 0
        for keys in parquet_frames(labels.path, ["timestamp", "user_min", "user_max"]):
            if not keys.timestamp.is_monotonic_increasing or (last_t is not None and len(keys) and keys.timestamp.iloc[0] < last_t):
                raise ValueError("预测快照必须按时间排列。")
            for t, group in keys.groupby("timestamp", sort=True):
                t = int(t)
                if t != last_t:
                    expression = ds.field("timestamp") < t
                    if previous is not None:
                        expression &= ds.field("timestamp") >= previous
                    for past in parquet_frames(paths[0], ["timestamp", "user_min", "user_max"], expression):
                        for pair, timestamp in past.groupby(["user_min", "user_max"]).timestamp.max().items():
                            last_contact[pair] = max(last_contact.get(pair, -1), int(timestamp))
                    previous = t
                    context = _history_context(processed, t)
                    last_t = t
                windows, neighbors, activity, positive_buckets, scans = context
                records = []
                for _, a, b in group.itertuples(index=False, name=None):
                    a, b = int(a), int(b)
                    if a < 0 or a >= b:
                        raise ValueError("特征配对必须使用有效且不同的规范化ID。")
                    pair = (a, b)
                    probability, ca, cb = None, None, None
                    if processed.report["scan_coverage_available"]:
                        ca = sum(scans[(a, bucket)] for bucket in range(7)) / (7 * 288)
                        cb = sum(scans[(b, bucket)] for bucket in range(7)) / (7 * 288)
                        eligible_buckets = {bucket for bucket in range(14) if min(scans[(a, bucket)], scans[(b, bucket)]) / 288 >= threshold}
                        if eligible_buckets:
                            probability = len(positive_buckets[pair] & eligible_buckets) / len(eligible_buckets)
                    weekday = (weekday_origin + t // DAY) % 7 if weekday_origin is not None else None
                    signal_n = windows[7]["rssi_n"][pair]
                    source_start = processed.report["source_timestamp_min"] - processed.report["time_origin_seconds"]
                    record = {
                        "timestamp": t, "user_min": a, "user_max": b,
                        **{f"contact_count_{window}d": windows[window]["count"][pair] for window in WINDOWS},
                        "contact_bins_1d": windows[1]["bins"][pair], "contact_bins_7d": windows[7]["bins"][pair],
                        "time_since_last_contact": t - last_contact[pair] if pair in last_contact else None,
                        "unique_contact_days_7d": windows[7]["days"][pair], "unique_contact_days_14d": windows[14]["days"][pair],
                        "historical_contact_probability": probability,
                        "rssi_mean_7d": windows[7]["rssi_sum"][pair] / signal_n if signal_n else None,
                        "rssi_max_7d": windows[7]["rssi_max"].get(pair), "sms_count_7d": None, "call_count_7d": None,
                        "prediction_day_index": t // DAY, "prediction_hour": t % DAY // 3600,
                        "relative_weekday": weekday, "is_relative_weekend": int(weekday >= 5) if weekday is not None else None,
                        "participant_a_activity_7d": activity[a], "participant_b_activity_7d": activity[b],
                        "common_neighbors_historical": len(neighbors[a] & neighbors[b]),
                        "historical_network_degree_a": len(neighbors[a]), "historical_network_degree_b": len(neighbors[b]),
                        "scan_coverage_a": ca, "scan_coverage_b": cb,
                        **{f"history_complete_{window}d": int(t - window * DAY >= source_start) for window in WINDOWS},
                    }
                    records.append(record)
                    count += 1
                    if len(records) == 10_000:
                        writer.write_table(pa.Table.from_pylist(records, schema=FEATURE_SCHEMA))
                        records.clear()
                if records:
                    writer.write_table(pa.Table.from_pylist(records, schema=FEATURE_SCHEMA))
        if file_signatures(paths) != signatures:
            raise RuntimeError("输入在特征生成期间改变，未发布缓存。")
        return {"rows": count, "feature_columns": list(FEATURE_NAMES), "history_windows_days": list(WINDOWS),
                "feature_interval": "[t - window, t)", "network_window_days": 7, "scan_coverage_window_days": 7,
                "historical_contact_probability_definition": "positive rolling 24h buckets / sufficiently observed buckets within past 14 days; unknown if denominator is zero",
                "communications_enabled": False, "weekday_origin": weekday_origin, "weekday_reference": weekday_reference,
                "missing_policy": "Unavailable source/communication/weekday/coverage values stay null; history_complete flags mark truncated history.",
                "future_fields_included": False}

    return cache_artifact(output, "features", identity, FEATURE_SCHEMA, produce)

"""Registry inference with time-valid models, historical keys and optional backtests."""

from collections import Counter
import json
import math
from pathlib import Path
import tempfile

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from src.model_registry import ModelRegistry
from src.feature_engineering import FEATURE_NAMES, build_features
from src.pipeline_cache import PipelineArtifact, parquet_frames
from src.explain import local_explanation
from src.temporal_split import TrainingDataError

DAY = 86400


def predict_probabilities(model_directory, features):
    return ModelRegistry.load(model_directory).predict_proba(features)[:, 1]


def model_information_deadline(manifest):
    try:
        return int(manifest["metadata"]["split"]["sets"]["validation"]["last_timestamp"]) + DAY
    except (KeyError, TypeError, ValueError) as exc:
        raise TrainingDataError("模型缺少可核实的训练/验证时间边界，不能进行时间回测。") from exc


def historical_pairs(processed, timestamp):
    pairs = set()
    for frame in parquet_frames(processed.directory / "contacts.parquet", ["user_min", "user_max"], ds.field("timestamp") < timestamp):
        pairs.update(frame.drop_duplicates().itertuples(index=False, name=None))
    return sorted(pairs)


def backtest_outcome(processed, timestamp, pair, *, min_scan_coverage=0.5):
    if not 0 < min_scan_coverage <= 1:
        raise TrainingDataError("回测覆盖率策略必须在 (0,1]。")
    end = processed.report["source_timestamp_max"] - processed.report["time_origin_seconds"]
    if timestamp + DAY > end:
        return {"outcome": "Unknown", "reason": "future_window_incomplete"}
    expression = (ds.field("timestamp") > timestamp) & (ds.field("timestamp") <= timestamp + DAY)
    contact_filter = expression & (ds.field("user_min") == pair[0]) & (ds.field("user_max") == pair[1])
    for frame in parquet_frames(processed.directory / "contacts.parquet", ["timestamp"], contact_filter):
        if len(frame):
            return {"outcome": "Contact", "reason": "observed_positive_evidence"}
    if not processed.report["scan_coverage_available"]:
        return {"outcome": "Unknown", "reason": "scan_coverage_unknown"}
    counts = Counter()
    for frame in parquet_frames(processed.directory / "observations.parquet", ["user_id", "scan_observed"], expression & ds.field("user_id").isin(pair)):
        counts.update(frame.loc[frame.scan_observed.eq(True), "user_id"].value_counts().to_dict())
    if min(counts[pair[0]], counts[pair[1]]) / 288 < min_scan_coverage:
        return {"outcome": "Unknown", "reason": "low_scan_coverage"}
    return {"outcome": "No Contact", "reason": "adequately_observed_no_contact"}


def predict_pair(processed, model_directory, timestamp, a, b, *, window_days=14, backtest=False):
    pair = tuple(sorted((int(a), int(b))))
    if pair[0] < 0 or pair[0] == pair[1] or timestamp < 0:
        raise TrainingDataError("请选择不同的有效匿名ID和非负预测时刻。")
    manifest = json.loads((Path(model_directory) / "manifest.json").read_text())
    provenance = manifest["metadata"].get("provenance", {})
    if provenance.get("dataset") != processed.report["dataset"]:
        raise TrainingDataError("模型与数据集不匹配。")
    if timestamp <= model_information_deadline(manifest):
        raise TrainingDataError("模型已使用该预测时点之后的训练/验证信息；请选择更晚时点或可用于该时点的历史模型。")
    if window_days != (manifest.get("feature_window_days") or 14):
        raise TrainingDataError("所选历史窗口与模型训练契约不匹配；请使用对应窗口的模型。")
    all_history = (ds.field("timestamp") < timestamp) & (ds.field("user_min") == pair[0]) & (ds.field("user_max") == pair[1])
    last_contact, historical_count, days = None, 0, Counter()
    for frame in parquet_frames(processed.directory / "contacts.parquet", ["timestamp"], all_history):
        if len(frame):
            last_contact = max(last_contact if last_contact is not None else -1, int(frame.timestamp.max()))
            recent = frame.loc[frame.timestamp.ge(timestamp - window_days * DAY)]
            historical_count += len(recent)
            days.update(recent.timestamp.floordiv(DAY).add(1).value_counts().to_dict())
    if last_contact is None:
        raise TrainingDataError("该配对在预测时点之前没有有效接触，当前Known Pair模型不适用。")
    model = ModelRegistry.load(model_directory)
    if {"sms_count_7d", "call_count_7d"} & set(model.feature_columns):
        raise TrainingDataError("当前部署未提供可靠通讯可用时间，不能对依赖通讯列的模型进行静默缺失替换。")
    policy = provenance.get("label_policy", {})
    feature_policy = provenance.get("feature_policy", {})
    with tempfile.TemporaryDirectory(prefix="encounter-prediction-") as temporary:
        keys_path = Path(temporary) / "prediction-keys.parquet"
        schema = pa.schema([("timestamp", pa.int64()), ("user_min", pa.int64()), ("user_max", pa.int64())])
        pq.write_table(pa.Table.from_pylist([{"timestamp": int(timestamp), "user_min": pair[0], "user_max": pair[1]}], schema=schema), keys_path)
        keys = PipelineArtifact(keys_path, {"policy": {"min_scan_coverage": policy.get("min_scan_coverage", 0.5)}}, False)
        features = build_features(processed, keys, Path(temporary) / "features", weekday_origin=feature_policy.get("weekday_origin"), weekday_reference=feature_policy.get("weekday_reference"))
        X = pd.read_parquet(features.path).loc[:, FEATURE_NAMES]
    probability = float(model.predict_proba(X)[0, 1])
    entropy = -sum(value * math.log2(value) for value in (probability, 1 - probability) if value > 0)
    first_day, last_day = max(0, timestamp - window_days * DAY) // DAY + 1, max(0, timestamp - 1) // DAY + 1
    result = {"timestamp": int(timestamp), "pair": list(pair), "probability": probability, "threshold": model.threshold,
              "prediction_entropy": entropy, "historical_contact_count": historical_count, "time_since_last_contact": timestamp - last_contact,
              "trend": [{"study_day": day, "contact_records": int(days[day])} for day in range(first_day, last_day + 1)],
              "explanation": local_explanation(model, X), "model_version": manifest["version"], "window_days": window_days,
              "source_kind": provenance.get("source_kind", "official_dataset_cache")}
    if backtest:
        result["actual_outcome"] = backtest_outcome(processed, timestamp, pair, min_scan_coverage=policy.get("min_scan_coverage", 0.5))
    return result

"""One-to-one cohort preparation and purged chronological snapshot splits."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.feature_engineering import FEATURE_NAMES

KEYS = ["timestamp", "user_min", "user_max"]


class TrainingDataError(ValueError):
    """Insufficient or mismatched prediction data; never silently relax eligibility."""


@dataclass
class TemporalSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    report: dict


def prepare_cohort(labels, features) -> pd.DataFrame:
    """Join only model-safe features; unknown/ineligible targets are never imputed."""
    label_frame = pd.read_parquet(labels.path)
    feature_frame = pd.read_parquet(features.path)
    expected = set(KEYS) | set(FEATURE_NAMES)
    if set(feature_frame.columns) != expected:
        raise TrainingDataError("特征表字段与历史特征白名单不匹配；拒绝目标或未来覆盖率字段。")
    for frame in (label_frame, feature_frame):
        if frame[KEYS].isna().any().any() or frame.duplicated(KEYS).any():
            raise TrainingDataError("标签/特征键存在缺失或重复。")
        if (frame.user_min < 0).any() or (frame.user_min >= frame.user_max).any():
            raise TrainingDataError("配对键必须是不同的非负规范化ID。")
    if not label_frame.label_24h.dropna().isin([0, 1]).all():
        raise TrainingDataError("目标标签必须为0、1或未知。")
    if label_frame.eligible_for_evaluation.isna().any() or not label_frame.eligible_for_evaluation.isin([True, False]).all():
        raise TrainingDataError("样本准入字段无效。")
    try:
        joined = feature_frame.merge(label_frame[KEYS + ["label_24h", "eligible_for_evaluation"]], on=KEYS, how="outer", validate="one_to_one", indicator=True)
    except pd.errors.MergeError as exc:
        raise TrainingDataError(f"标签/特征不能一一对应：{exc}") from exc
    if not joined._merge.eq("both").all():
        raise TrainingDataError("标签/特征键不完全一致，请重新生成对应缓存。")
    cohort = joined.loc[joined.eligible_for_evaluation.eq(True) & joined.label_24h.notna(), KEYS + list(FEATURE_NAMES) + ["label_24h"]].copy()
    if cohort.empty:
        raise TrainingDataError("没有覆盖策略允许且标签已知的训练样本；不能把未知观测改成负例。")
    cohort["label_24h"] = cohort.label_24h.astype("int8")
    cohort = cohort.sort_values(KEYS).reset_index(drop=True)
    cohort.attrs["source_rows"] = len(joined)
    cohort.attrs["excluded_rows"] = len(joined) - len(cohort)
    return cohort


def chronological_split(frame: pd.DataFrame, *, fractions=(0.6, 0.2, 0.2), horizon_hours=24) -> TemporalSplit:
    """Split unique snapshot times, purging inclusive label windows at boundaries."""
    if len(fractions) != 3 or any(value <= 0 for value in fractions) or not np.isclose(sum(fractions), 1):
        raise TrainingDataError("切分比例必须为三个正数且总和为1。")
    if horizon_hours != 24:
        raise TrainingDataError("当前标签仅支持24小时预测窗口。")
    times = np.sort(frame.timestamp.unique())
    first, second = int(len(times) * fractions[0]), int(len(times) * (fractions[0] + fractions[1]))
    if first < 1 or second <= first or second >= len(times):
        raise TrainingDataError("有效预测时点不足，不能形成训练/验证/测试三个时间段。")
    validation_start, test_start = int(times[first]), int(times[second])
    horizon = horizon_hours * 3600
    train = frame.loc[(frame.timestamp < validation_start) & (frame.timestamp + horizon < validation_start)].copy()
    validation = frame.loc[(frame.timestamp >= validation_start) & (frame.timestamp < test_start) & (frame.timestamp + horizon < test_start)].copy()
    test = frame.loc[frame.timestamp >= test_start].copy()
    if any(part.empty for part in (train, validation, test)):
        raise TrainingDataError("清除跨边界标签窗口后某集合为空；请增加有效观测时长，不能跳过防泄漏隔离。")
    report = {
        "method": "chronological_unique_snapshot_times", "requested_fractions": list(fractions), "horizon_hours": horizon_hours,
        "validation_start": validation_start, "test_start": test_start, "purged_rows": len(frame) - len(train) - len(validation) - len(test),
        "source_rows": frame.attrs.get("source_rows", len(frame)), "excluded_rows": frame.attrs.get("excluded_rows", 0),
        "sets": {name: {"rows": len(part), "first_timestamp": int(part.timestamp.min()), "last_timestamp": int(part.timestamp.max())}
                 for name, part in (("train", train), ("validation", validation), ("test", test))},
    }
    return TemporalSplit(*(part.sort_values(KEYS).reset_index(drop=True) for part in (train, validation, test)), report)


def validation_partition(validation: pd.DataFrame, *, calibration_fraction=0.5, horizon_hours=24):
    """Early validation for calibration, later validation for threshold/selection."""
    if not 0 < calibration_fraction < 1:
        raise TrainingDataError("校准比例必须在 (0,1)。")
    times = np.sort(validation.timestamp.unique())
    cutoff_index = int(len(times) * calibration_fraction)
    if cutoff_index < 1 or cutoff_index >= len(times):
        raise TrainingDataError("验证时点不足，无法独立校准与选择阈值。")
    cutoff = int(times[cutoff_index])
    calibration = validation.loc[validation.timestamp + horizon_hours * 3600 < cutoff].copy()
    tuning = validation.loc[validation.timestamp >= cutoff].copy()
    if calibration.empty or tuning.empty:
        raise TrainingDataError("验证集在校准/阈值时段隔离后为空；增加验证时长或明确禁用校准。")
    return calibration, tuning

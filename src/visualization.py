"""Chunked, retrospective exploration of T05 caches and scoped Plotly figures."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pyarrow.parquet as pq

DAY = 86400


def _frames(path, columns, batch_size=100_000):
    for batch in pq.ParquetFile(path).iter_batches(batch_size=batch_size, columns=columns):
        yield batch.to_pandas()


def exploration_options(directory: str | Path, report: dict) -> dict:
    users = set()
    for frame in _frames(Path(directory) / "coverage.parquet", ["user_id"]):
        users.update(int(user) for user in frame.user_id)
    origin = report["time_origin_seconds"]
    return {
        "users": sorted(users),
        "first_day": (report["source_timestamp_min"] - origin) // DAY + 1,
        "last_day": (report["source_timestamp_max"] - origin) // DAY + 1,
    }


@dataclass
class Exploration:
    rows: int
    daily: pd.DataFrame
    hourly: pd.DataFrame
    pairs: pd.DataFrame
    activity: pd.DataFrame
    rssi: pd.DataFrame
    coverage: pd.DataFrame
    coverage_mean: float | None


def summarize_exploration(directory: str | Path, report: dict, days: tuple[int, int], *, users=(), pair=None) -> Exploration:
    """Count observed records without constructing unobserved pairs or labels.

    User filtering retains contacts with either endpoint selected. Pair filtering
    intersects this condition. Coverage uses selected users, or pair endpoints if
    no users were selected; observations are never gated on a contact occurring.
    """
    start, end = days
    if start < 1 or end < start:
        raise ValueError("Study Day 范围无效。")
    users = set(int(user) for user in users)
    if any(user < 0 for user in users):
        raise ValueError("参与者 ID 必须非负。")
    if pair is not None:
        pair = tuple(sorted(int(user) for user in pair))
        if len(pair) != 2 or pair[0] < 0 or pair[0] == pair[1]:
            raise ValueError("请选择两名不同的有效参与者。")
    directory = Path(directory)
    daily, hourly, pairs, activity = Counter(), Counter(), Counter(), Counter()
    rows = 0
    low, high = report["rssi_summary"]["min"], report["rssi_summary"]["max"]
    bins = np.linspace(low, high, 31) if low is not None and low < high else np.array([low - 0.5, low + 0.5]) if low is not None else None
    signal_counts = np.zeros(len(bins) - 1, dtype=np.int64) if bins is not None else None
    for frame in _frames(directory / "contacts.parquet", ["timestamp", "user_min", "user_max", "rssi"]):
        mask = frame.timestamp.ge((start - 1) * DAY) & frame.timestamp.lt(end * DAY)
        if users:
            mask &= frame.user_min.isin(users) | frame.user_max.isin(users)
        if pair is not None:
            mask &= frame.user_min.eq(pair[0]) & frame.user_max.eq(pair[1])
        selected = frame.loc[mask]
        rows += len(selected)
        daily.update(selected.timestamp.floordiv(DAY).add(1).value_counts().to_dict())
        hourly.update(selected.timestamp.mod(DAY).floordiv(3600).value_counts().to_dict())
        pairs.update(selected.groupby(["user_min", "user_max"]).size().to_dict())
        activity.update(selected.user_min.value_counts().to_dict())
        activity.update(selected.user_max.value_counts().to_dict())
        if bins is not None:
            signal_counts += np.histogram(selected.rssi.dropna(), bins=bins)[0]

    coverage_users = users or set(pair or ())
    # sum coverage, known rows, positive rows, zero rows, unknown rows
    coverage_counts = {day: [0.0, 0, 0, 0, 0] for day in range(start, end + 1)}
    for frame in _frames(directory / "coverage.parquet", ["user_id", "study_day", "scan_coverage"]):
        mask = frame.study_day.between(start, end)
        if coverage_users:
            mask &= frame.user_id.isin(coverage_users)
        for day, group in frame.loc[mask].groupby("study_day"):
            values = group.scan_coverage
            counts = coverage_counts[int(day)]
            counts[0] += float(values.sum())
            counts[1] += int(values.notna().sum())
            counts[2] += int(values.gt(0).sum())
            counts[3] += int(values.eq(0).sum())
            counts[4] += int(values.isna().sum())
    coverage = pd.DataFrame([
        {"study_day": day, "mean_scan_coverage": counts[0] / counts[1] if counts[1] else np.nan,
         "有扫描记录": counts[2], "无扫描记录": counts[3], "覆盖率未知": counts[4]}
        for day, counts in coverage_counts.items()
    ])
    known_count = sum(counts[1] for counts in coverage_counts.values())
    return Exploration(
        rows,
        pd.DataFrame({"study_day": range(start, end + 1), "contact_records": [daily[day] for day in range(start, end + 1)]}),
        pd.DataFrame({"hour": range(24), "contact_records": [hourly[hour] for hour in range(24)]}),
        pd.DataFrame([(int(a), int(b), count) for (a, b), count in sorted(pairs.items())], columns=["user_min", "user_max", "contact_records"]),
        pd.DataFrame(sorted(activity.items(), key=lambda item: (-item[1], item[0])), columns=["user_id", "contact_records"]),
        pd.DataFrame({"rssi": (bins[:-1] + bins[1:]) / 2, "records": signal_counts}) if bins is not None else pd.DataFrame(columns=["rssi", "records"]),
        coverage,
        sum(counts[0] for counts in coverage_counts.values()) / known_count if known_count else None,
    )


def exploration_figures(data: Exploration, scope: str, *, top_n: int = 20) -> dict:
    """Return a bounded heatmap/ranking and full-scope aggregates; never sample rows."""
    labels = {"study_day": "Study Day", "hour": "研究日内小时", "contact_records": "接触记录数", "user_id": "匿名参与者 ID"}
    figures = {
        "每日接触趋势": px.line(data.daily, x="study_day", y="contact_records", markers=True, labels=labels),
        "每小时接触趋势": px.bar(data.hourly, x="hour", y="contact_records", labels=labels),
    }
    if not data.pairs.empty:
        frequency = data.pairs.contact_records.value_counts().sort_index().rename_axis("frequency").reset_index(name="pairs")
        figures["配对接触频率分布"] = px.bar(frequency, x="frequency", y="pairs", labels={"frequency": "每配对接触记录数", "pairs": "有记录的配对数"})
        ranked = data.activity.head(top_n).copy()
        ranked["user_id"] = ranked.user_id.astype(str)
        figures[f"参与者活跃度 · Top {top_n}"] = px.bar(ranked, x="user_id", y="contact_records", labels=labels)
        ids = ranked.user_id.tolist()
        positions = {int(user): index for index, user in enumerate(ids)}
        matrix = np.zeros((len(ids), len(ids)), dtype=np.int64)
        for a, b, count in data.pairs.itertuples(index=False, name=None):
            if a in positions and b in positions:
                matrix[positions[a], positions[b]] = matrix[positions[b], positions[a]] = count
        figures[f"历史接触记录热力图 · Top {top_n}"] = go.Figure(go.Heatmap(
            z=matrix, x=ids, y=ids, colorbar={"title": "接触记录数"},
            hovertemplate="参与者 A：%{x}<br>参与者 B：%{y}<br>接触记录数：%{z}<extra></extra>",
        ))
        figures[f"历史接触记录热力图 · Top {top_n}"].update_layout(xaxis_title="匿名参与者 ID", yaxis_title="匿名参与者 ID")
    if not data.rssi.empty and data.rssi.records.sum():
        figures["RSSI 分布"] = px.bar(data.rssi, x="rssi", y="records", labels={"rssi": "RSSI（原始单位，分箱中心）", "records": "接触记录数"})
    if data.coverage_mean is not None:
        figures["扫描记录覆盖率"] = px.line(data.coverage, x="study_day", y="mean_scan_coverage", markers=True, labels={"study_day": "Study Day", "mean_scan_coverage": "平均扫描记录覆盖率"})
        figures["扫描记录覆盖率"].update_yaxes(tickformat=".0%", range=[0, 1])
    missing = data.coverage.melt(id_vars="study_day", value_vars=["有扫描记录", "无扫描记录", "覆盖率未知"], var_name="观测状态", value_name="participants")
    figures["扫描与缺失观测状态"] = px.bar(missing, x="study_day", y="participants", color="观测状态", labels={"study_day": "Study Day", "participants": "参与者数"})
    for title, figure in figures.items():
        figure.update_layout(title={"text": f"{title}<br><sup>{scope}</sup>"}, margin={"t": 85})
        if title in {"每日接触趋势", "每小时接触趋势", "扫描记录覆盖率", "扫描与缺失观测状态"}:
            figure.update_xaxes(dtick=1)
    return figures

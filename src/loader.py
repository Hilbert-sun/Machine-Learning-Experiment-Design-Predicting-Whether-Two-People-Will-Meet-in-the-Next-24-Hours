"""Source-aware, chunked parsing and schema validation; no cleaning or label creation."""

from dataclasses import asdict, dataclass
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

SCHEMAS = {
    "bluetooth": ("timestamp", "user_a", "user_b", "rssi"),
    "calls": ("timestamp", "user_a", "user_b", "duration"),
    "sms": ("timestamp", "user_a", "user_b"),
    "proximity": ("timestamp", "user_a", "user_b", "class_a", "class_b"),
}
FILE_KINDS = {
    "Copenhagen": {"bt_symmetric.csv": "bluetooth", "bt.csv": "bluetooth", "calls.csv": "calls", "sms.csv": "sms"},
    "SocioPatterns": {"HighSchool2013_proximity_net.csv.gz": "proximity", "HighSchool2013_proximity_net.csv": "proximity"},
}
ALIASES = {"calls": {"caller": "user_a", "callee": "user_b"}, "sms": {"sender": "user_a", "recipient": "user_b"}}


class SchemaError(ValueError):
    """The source cannot be interpreted without silently guessing fields."""


def source_kind(path: str | Path, dataset: str) -> str:
    try:
        return FILE_KINDS[dataset][Path(path).name]
    except KeyError as exc:
        raise SchemaError(f"不支持的数据集/文件：{dataset} / {Path(path).name}。请使用官方原始文件名。") from exc


def supported_files(directory: str | Path, dataset: str) -> list[Path]:
    if dataset not in FILE_KINDS:
        raise SchemaError(f"不支持的数据集：{dataset}")
    return [
        Path(directory) / name for name in FILE_KINDS[dataset]
        if (Path(directory) / name).is_file() and not (Path(directory) / name).is_symlink()
    ]


def _normalize(frame: pd.DataFrame, kind: str, offset: int) -> pd.DataFrame:
    expected = SCHEMAS[kind]
    if kind == "proximity":
        if len(frame.columns) != len(expected):
            raise SchemaError(f"SocioPatterns 接触行应有5个空白分隔字段，实际为 {len(frame.columns)}。")
        frame.columns = expected
    else:
        names = [str(name).strip().removeprefix("#").strip() for name in frame.columns]
        frame.columns = [ALIASES.get(kind, {}).get(name, name) for name in names]
        if len(set(frame.columns)) != len(frame.columns) or set(frame.columns) != set(expected):
            raise SchemaError(f"{kind} 字段不匹配：实际 {names}；需要 {list(expected)}（允许已验证的源字段别名）。")
    frame = frame.loc[:, list(expected)].copy()

    def invalid(mask, column, reason):
        if mask.any():
            index = int(np.flatnonzero(mask.to_numpy())[0]) + offset + 1
            raise SchemaError(f"数据行 {index} 的 {column} {reason}。")

    for column in expected:
        if column.startswith("class_"):
            invalid(frame[column].isna() | frame[column].str.strip().eq(""), column, "缺失")
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        invalid(numeric.isna() | ~np.isfinite(numeric), column, "缺失或不是有限数值")
        if column != "rssi":
            invalid(numeric.mod(1).ne(0), column, "必须是整数")
            invalid((numeric < -(2**63)) | (numeric >= 2**63), column, "超出64位整数范围")
            numeric = numeric.astype("int64")
        frame[column] = numeric

    invalid(frame["timestamp"].lt(0), "timestamp", "不能为负数")
    invalid(frame["user_a"].lt(0), "user_a", "必须是非负参与者ID")
    minimum_b = -2 if kind == "bluetooth" else 0
    invalid(frame["user_b"].lt(minimum_b), "user_b", "不是有效参与者ID或已知蓝牙扫描标记")
    if kind == "calls":
        invalid(frame["duration"].lt(-1), "duration", "不能小于 -1（未接来电）")
    return frame


def iter_source_chunks(path: str | Path, dataset: str, *, kind: str | None = None, chunksize: int = 100_000):
    """Yield validated typed chunks, preserving direction, sentinels and duplicates.

    Copenhagen timestamps remain relative seconds; SocioPatterns remain UNIX seconds.
    No IDs, timestamps or paired rows are synthesized or discarded.
    """
    path = Path(path)
    if chunksize < 1:
        raise ValueError("chunksize must be positive")
    kind = kind or source_kind(path, dataset)
    allowed = {"bluetooth", "calls", "sms"} if dataset == "Copenhagen" else {"proximity"} if dataset == "SocioPatterns" else set()
    if kind not in allowed:
        raise SchemaError(f"数据集 {dataset} 与文件类型 {kind} 不匹配。")
    options = {"sep": r"\s+", "header": None} if kind == "proximity" else {"sep": ",", "header": 0}
    offset = 0
    try:
        with warnings.catch_warnings():
            # pandas may otherwise drop an extra field when index_col=False.
            warnings.simplefilter("error", pd.errors.ParserWarning)
            with pd.read_csv(
                path, dtype=str, index_col=False, chunksize=chunksize,
                # The C engine can silently truncate extra fields at chunk boundaries.
                # Python parsing plus ParserWarning-as-error checks every chunk's width.
                compression="infer", on_bad_lines="error", engine="python", **options,
            ) as reader:
                for frame in reader:
                    normalized = _normalize(frame, kind, offset)
                    offset += len(normalized)
                    if len(normalized):
                        yield normalized
    except SchemaError:
        raise
    except (OSError, EOFError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError, pd.errors.ParserWarning) as exc:
        raise SchemaError(f"{path.name} 无法解析：{exc}。请检查分隔符、字段数量和压缩文件完整性。") from exc
    if offset == 0:
        raise SchemaError(f"{path.name} 没有数据行。")


@dataclass
class ValidationReport:
    file: str
    kind: str
    rows: int
    columns: list[str]
    dtypes: dict[str, str]
    timestamp_min: int
    timestamp_max: int
    time_basis: str
    empty_scans: int
    external_scans: int
    self_contacts: int
    rssi_min: float | None
    rssi_max: float | None
    preview: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def validate_file(path: str | Path, dataset: str, *, kind: str | None = None, chunksize: int = 100_000) -> ValidationReport:
    kind = kind or source_kind(path, dataset)
    count = empty = external = self_contacts = 0
    time_min = time_max = rssi_min = rssi_max = None
    preview = []
    columns = []
    dtypes = {}
    for frame in iter_source_chunks(path, dataset, kind=kind, chunksize=chunksize):
        count += len(frame)
        columns = list(frame.columns)
        dtypes = {key: str(value) for key, value in frame.dtypes.items()}
        low, high = int(frame.timestamp.min()), int(frame.timestamp.max())
        time_min = low if time_min is None else min(time_min, low)
        time_max = high if time_max is None else max(time_max, high)
        self_contacts += int(frame.user_a.eq(frame.user_b).sum())
        if kind == "bluetooth":
            empty += int(frame.user_b.eq(-1).sum())
            external += int(frame.user_b.eq(-2).sum())
            low_rssi, high_rssi = float(frame.rssi.min()), float(frame.rssi.max())
            rssi_min = low_rssi if rssi_min is None else min(rssi_min, low_rssi)
            rssi_max = high_rssi if rssi_max is None else max(rssi_max, high_rssi)
        if len(preview) < 10:
            preview.extend(frame.head(10 - len(preview)).to_dict(orient="records"))
    return ValidationReport(
        Path(path).name, kind, count, columns, dtypes, time_min, time_max,
        "relative_seconds" if dataset == "Copenhagen" else "unix_seconds",
        empty, external, self_contacts, rssi_min, rssi_max, preview,
    )

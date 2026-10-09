"""Canonical contact events and observation evidence, with bounded-memory caching."""

from dataclasses import dataclass
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.loader import SchemaError, iter_source_chunks, source_kind

VERSION = 1
DAY_SECONDS = 86400
CONTACT_SCHEMA = pa.schema([
    ("timestamp", pa.int64()), ("source_timestamp", pa.int64()),
    ("user_min", pa.int64()), ("user_max", pa.int64()), ("rssi", pa.float64()),
    ("class_min", pa.string()), ("class_max", pa.string()),
])
OBSERVATION_SCHEMA = pa.schema([
    ("timestamp", pa.int64()), ("user_id", pa.int64()), ("scan_observed", pa.bool_()),
])
COVERAGE_SCHEMA = pa.schema([
    ("user_id", pa.int64()), ("study_day", pa.int64()), ("recorded_bins", pa.int64()),
    ("expected_scan_bins", pa.int64()), ("scan_coverage", pa.float64()),
])


@dataclass
class CleanedChunk:
    contacts: pd.DataFrame
    observations: pd.DataFrame
    invalid_id_rows: int
    self_contact_rows: int


@dataclass
class ProcessedDataset:
    directory: Path
    report: dict
    cached: bool


def clean_contact_chunk(frame: pd.DataFrame, dataset: str) -> CleanedChunk:
    """Clean typed contact rows from the loader without changing input data.

    Different RSSI values at one pair/time remain distinct measurements. Exact
    canonical duplicates are removed by the disk-backed pipeline across chunks.
    """
    if dataset not in {"Copenhagen", "SocioPatterns"}:
        raise ValueError(f"不支持的数据集：{dataset}")
    valid_ids = frame.user_a.ge(0) & frame.user_b.ge(0)
    self_contact = valid_ids & frame.user_a.eq(frame.user_b)
    valid = frame.loc[valid_ids & ~self_contact].copy()
    swapped = valid.user_a.gt(valid.user_b)
    contacts = pd.DataFrame({
        "timestamp": valid.timestamp,
        "user_min": valid[["user_a", "user_b"]].min(axis=1),
        "user_max": valid[["user_a", "user_b"]].max(axis=1),
        "rssi": valid.rssi if dataset == "Copenhagen" else np.nan,
        "class_min": np.where(swapped, valid.class_b, valid.class_a) if dataset == "SocioPatterns" else None,
        "class_max": np.where(swapped, valid.class_a, valid.class_b) if dataset == "SocioPatterns" else None,
    }).reset_index(drop=True)

    if dataset == "Copenhagen":
        # A receiver ID is not evidence that this receiver performed a scan.
        observations = frame.loc[frame.user_a.ge(0), ["timestamp", "user_a"]].rename(columns={"user_a": "user_id"}).copy()
        observations["timestamp"] = observations.timestamp.floordiv(300).mul(300)
        observations["scan_observed"] = True
    else:
        observations = pd.concat([
            valid[["timestamp", "user_a"]].rename(columns={"user_a": "user_id"}),
            valid[["timestamp", "user_b"]].rename(columns={"user_b": "user_id"}),
        ], ignore_index=True)
        observations["timestamp"] = observations.timestamp.floordiv(20).mul(20)
        observations["scan_observed"] = pd.NA
    observations = observations.drop_duplicates(["timestamp", "user_id"]).reset_index(drop=True)
    return CleanedChunk(contacts, observations, int((~valid_ids).sum()), int(self_contact.sum()))


def _identity(source: Path, dataset: str) -> dict:
    stat = source.stat()
    return {"version": VERSION, "dataset": dataset, "source": str(source.resolve()), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _cache_location(source: Path, dataset: str, output: Path):
    identity = _identity(source, dataset)
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    base = output / dataset.lower()
    return identity, base, base / f"{key}.json"


def cached_dataset(source: str | Path, dataset: str, output: str | Path) -> ProcessedDataset | None:
    """A cache is current only for the same source signature and complete artifacts."""
    identity, base, manifest = _cache_location(Path(source), dataset, Path(output))
    try:
        record = json.loads(manifest.read_text())
        folder = base / record["directory"]
        if record["identity"] != identity or folder.parent != base:
            return None
        if not all((folder / name).is_file() for name in ("contacts.parquet", "observations.parquet", "coverage.parquet", "quality.json")):
            return None
        return ProcessedDataset(folder, record["report"], True)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _export(connection, query, path, schema, chunksize):
    cursor = connection.execute(query)
    names = [column[0] for column in cursor.description]
    boolean_columns = [field.name for field in schema if pa.types.is_boolean(field.type)]
    count = 0
    with pq.ParquetWriter(path, schema) as writer:
        while rows := cursor.fetchmany(chunksize):
            records = [dict(zip(names, row)) for row in rows]
            for record in records:
                for name in boolean_columns:
                    if record[name] is not None:
                        record[name] = bool(record[name])
            writer.write_table(pa.Table.from_pylist(records, schema=schema))
            count += len(rows)
    return count


def preprocess_contacts(source: str | Path, dataset: str, output: str | Path, *, chunksize: int = 100_000, progress=None) -> ProcessedDataset:
    """Write canonical contacts, sparse observation evidence and daily quality coverage.

    SQLite removes exact duplicates across chunks without holding all events in
    memory. A manifest is published only after all outputs complete successfully.
    """
    source, output = Path(source), Path(output)
    kind = source_kind(source, dataset)
    if kind not in {"bluetooth", "proximity"}:
        raise SchemaError("预处理需要主接触文件；电话和短信保留在原始目录供后续任务使用。")
    if chunksize < 1:
        raise ValueError("chunksize must be positive")
    previous = cached_dataset(source, dataset, output)
    if previous:
        return previous
    identity, base, manifest = _cache_location(source, dataset, output)
    base.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=manifest.stem + "-", dir=base))
    raw_rows = invalid_rows = self_rows = candidate_rows = empty_scans = external_scans = 0
    raw_min = raw_max = None
    missing_values = {}
    manifest_tmp = None
    try:
        with closing(sqlite3.connect(folder / "working.sqlite")) as connection:
            connection.executescript("""
                CREATE TABLE contacts (
                    timestamp INTEGER, user_min INTEGER, user_max INTEGER,
                    rssi TEXT NOT NULL, class_min TEXT NOT NULL, class_max TEXT NOT NULL,
                    PRIMARY KEY (timestamp, user_min, user_max, rssi, class_min, class_max)
                ) WITHOUT ROWID;
                CREATE TABLE observations (timestamp INTEGER, user_id INTEGER, PRIMARY KEY (timestamp, user_id)) WITHOUT ROWID;
                CREATE TABLE participants (user_id INTEGER PRIMARY KEY);
            """)
            for frame in iter_source_chunks(source, dataset, chunksize=chunksize):
                cleaned = clean_contact_chunk(frame, dataset)
                for name in frame.columns:
                    missing_values[name] = missing_values.get(name, 0) + int(frame[name].isna().sum())
                raw_rows += len(frame)
                invalid_rows += cleaned.invalid_id_rows
                self_rows += cleaned.self_contact_rows
                candidate_rows += len(cleaned.contacts)
                if dataset == "Copenhagen":
                    empty_scans += int(frame.user_b.eq(-1).sum())
                    external_scans += int(frame.user_b.eq(-2).sum())
                low, high = int(frame.timestamp.min()), int(frame.timestamp.max())
                raw_min = low if raw_min is None else min(raw_min, low)
                raw_max = high if raw_max is None else max(raw_max, high)
                connection.executemany("INSERT OR IGNORE INTO contacts VALUES (?, ?, ?, ?, ?, ?)", (
                    (int(t), int(a), int(b), "" if pd.isna(rssi) else format(float(rssi), ".17g"), ca or "", cb or "")
                    for t, a, b, rssi, ca, cb in cleaned.contacts.itertuples(index=False, name=None)
                ))
                connection.executemany("INSERT OR IGNORE INTO observations VALUES (?, ?)", (
                    (int(t), int(user)) for t, user in cleaned.observations[["timestamp", "user_id"]].itertuples(index=False, name=None)
                ))
                participants = set(cleaned.observations.user_id) | set(cleaned.contacts.user_min) | set(cleaned.contacts.user_max)
                connection.executemany("INSERT OR IGNORE INTO participants VALUES (?)", ((int(user),) for user in participants))
                connection.commit()
                if progress:
                    progress(raw_rows)
            if _identity(source, dataset) != identity:
                raise RuntimeError("源文件在处理期间发生改变，请重新验证后重试。")

            origin = 0 if dataset == "Copenhagen" else raw_min // DAY_SECONDS * DAY_SECONDS
            day_start, day_end = (raw_min - origin) // DAY_SECONDS + 1, (raw_max - origin) // DAY_SECONDS + 1
            contact_count = _export(connection, f"""
                SELECT timestamp - {origin} AS timestamp, timestamp AS source_timestamp,
                       user_min, user_max, CAST(NULLIF(rssi, '') AS REAL) AS rssi,
                       NULLIF(class_min, '') AS class_min, NULLIF(class_max, '') AS class_max
                FROM contacts ORDER BY timestamp, user_min, user_max, rssi, class_min, class_max
            """, folder / "contacts.parquet", CONTACT_SCHEMA, chunksize)
            observed = "1" if dataset == "Copenhagen" else "NULL"
            _export(connection, f"SELECT timestamp - {origin} AS timestamp, user_id, {observed} AS scan_observed FROM observations ORDER BY timestamp, user_id",
                    folder / "observations.parquet", OBSERVATION_SCHEMA, chunksize)

            expected = "288" if dataset == "Copenhagen" else "NULL"
            coverage = "COALESCE(counts.bins, 0) / 288.0" if dataset == "Copenhagen" else "NULL"
            _export(connection, f"""
                WITH RECURSIVE days(day) AS (SELECT {day_start} UNION ALL SELECT day + 1 FROM days WHERE day < {day_end}),
                counts AS (SELECT user_id, (timestamp - {origin}) / {DAY_SECONDS} + 1 AS day, COUNT(*) AS bins
                           FROM observations GROUP BY user_id, day)
                SELECT p.user_id, days.day AS study_day, COALESCE(counts.bins, 0) AS recorded_bins,
                       {expected} AS expected_scan_bins, {coverage} AS scan_coverage
                FROM participants p CROSS JOIN days LEFT JOIN counts ON counts.user_id = p.user_id AND counts.day = days.day
                ORDER BY p.user_id, days.day
            """, folder / "coverage.parquet", COVERAGE_SCHEMA, chunksize)
            report = {
                "dataset": dataset, "source_file": source.name, "input_rows": raw_rows,
                "invalid_id_rows": invalid_rows, "self_contact_rows": self_rows,
                "empty_scan_rows": empty_scans, "external_device_rows": external_scans,
                "duplicate_contact_rows": candidate_rows - contact_count, "contact_rows": contact_count,
                "participants": connection.execute("SELECT COUNT(*) FROM participants").fetchone()[0],
                "observation_bins": connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
                "source_timestamp_min": raw_min, "source_timestamp_max": raw_max, "time_origin_seconds": origin,
                "timestamp_basis": "relative_seconds", "source_time_basis": "relative_seconds" if dataset == "Copenhagen" else "unix_seconds",
                "scan_coverage_available": dataset == "Copenhagen",
                "coverage_definition": "reporter scan bins / 288 per full study day; partial days use the same denominator" if dataset == "Copenhagen" else "unknown: positive contacts are not scan logs",
                "rssi_summary": dict(zip(("min", "max", "mean"), connection.execute("SELECT MIN(CAST(NULLIF(rssi, '') AS REAL)), MAX(CAST(NULLIF(rssi, '') AS REAL)), AVG(CAST(NULLIF(rssi, '') AS REAL)) FROM contacts").fetchone())),
                "daily_contacts": [dict(zip(("study_day", "contact_rows"), row)) for row in connection.execute(f"SELECT (timestamp - {origin}) / {DAY_SECONDS} + 1 AS day, COUNT(*) FROM contacts GROUP BY day ORDER BY day")],
                "missing_values": missing_values,
                "unavailable_fields": ["rssi"] if dataset == "SocioPatterns" else ["class_min", "class_max"],
                "coverage_use": "retrospective quality summary only; future prediction windows must use sparse observations within their own time bounds",
            }
        (folder / "working.sqlite").unlink()
        (folder / "quality.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=base, suffix=".tmp", delete=False) as handle:
            manifest_tmp = Path(handle.name)
            json.dump({"identity": identity, "directory": folder.name, "report": report}, handle, ensure_ascii=False)
        os.replace(manifest_tmp, manifest)
        return ProcessedDataset(folder, report, False)
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        if isinstance(exc, sqlite3.Error):
            raise RuntimeError(f"本地预处理存储失败：{exc}") from exc
        raise
    finally:
        if manifest_tmp is not None:
            manifest_tmp.unlink(missing_ok=True)

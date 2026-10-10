"""T28 inference from historical contacts only; offline evaluation cohorts are never inputs."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from numbers import Integral
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from src.baseline_audit import sha256
from src.model_registry import ModelRegistry
from src.pipeline_cache import parquet_frames
from src.temporal_split import TrainingDataError
from src.window_cohort import DAY, KEYS, past_pairs
from src.window_features import FEATURE_VERSION, WINDOW_FEATURES, snapshot_features
from src.snapshot_manager import snapshot_context, processed_paths, model_paths, resolve_path, read_json

MODES = ("historical_blind_replay", "prospective_inference")
NAMESPACES = {"Copenhagen": "copenhagen", "SocioPatterns": "highschool2013"}


class InferenceError(TrainingDataError):
    """A model/time/source contract is missing or incompatible; no probability is emitted."""


@dataclass(frozen=True)
class ClockAnchor:
    """Externally verified wall time of relative second zero, never inferred from file mtime."""
    origin_utc: datetime
    reference: str


@dataclass(frozen=True)
class ModelContract:
    dataset_id: str
    history_window_days: int
    label_information_ends: dict
    min_scan_coverage: float
    time_origin_seconds: int
    model_sha256: str
    calibration_method: str | None
    evidence: str

    @property
    def information_deadline(self):
        return max(self.label_information_ends.values())


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
        raise InferenceError(f"{name} must be a nonnegative integer.")
    return int(value)


def _source(processed, dataset_id):
    expected = NAMESPACES.get(processed.report.get("dataset"))
    if expected is None or dataset_id != expected:
        raise InferenceError("dataset_namespace_mismatch: source population/sensor is not this dataset.")


def _pair(a, b):
    pair = tuple(sorted((_integer(a, "participant"), _integer(b, "participant"))))
    if pair[0] == pair[1]:
        raise InferenceError("Participants must be distinct.")
    return pair


def as_of_candidates(processed, timestamp, *, dataset_id):
    """All canonical pairs with contacts in [t-1d,t), independent of scan/label evidence."""
    t = _integer(timestamp, "timestamp")
    _source(processed, dataset_id)
    try:
        from src.safe_cache import SafeCache
        path = processed.directory/'contacts.parquet'
        with snapshot_context([path], {'dataset_id': dataset_id, 'timestamp': t, 'candidate_policy': '[t-1d,t)'}) as snapshot:
            identity = {'object': 'asof_candidates', 'dataset_id': dataset_id, 'timestamp': t,
                        'source_sha256': snapshot.hashes[str(path.resolve())], 'candidate_policy': '[t-1d,t)', 'version': 1}
            pairs = SafeCache().get(identity, lambda: {'pairs': past_pairs(processed, t, 1)}, guard=snapshot.check_live)['pairs']
    except OSError as exc:
        raise InferenceError("historical_contact_evidence_missing") from exc
    if (pairs.user_min < 0).any() or (pairs.user_min >= pairs.user_max).any():
        raise InferenceError("Contacts are not canonical validated pairs.")
    return pairs.assign(dataset_id=dataset_id, timestamp=t).loc[:, KEYS].reset_index(drop=True)


def as_of_features(processed, timestamp, *, dataset_id, windows=(1, 3, 7), min_scan_coverage=0.5):
    """Generate inputs afresh with frozen bounded computation, never a stored cohort/bank.

    No future horizon/completeness/eligibility check is performed. Source start is a
    historical span bound; future source end and future scan coverage are not read.
    """
    t = _integer(timestamp, "timestamp")
    if not windows or len(set(windows)) != len(windows) or any(type(w) is not int or w not in (1, 3, 7) for w in windows):
        raise InferenceError("Windows must be distinct1/3/7-day integers.")
    if not np.isfinite(min_scan_coverage) or not 0 < min_scan_coverage <= 1:
        raise InferenceError("Coverage threshold must be in (0,1].")
    _source(processed, dataset_id)
    from src.bounded_history import BANKS, bounded_reader
    from src.safe_cache import SafeCache, frame_identity
    prepared = BANKS.get()
    if prepared is not None and prepared['directory'] == processed.directory.resolve() and prepared['t'] == t and prepared['coverage'] == min_scan_coverage and set(windows) <= set(prepared['banks']):
        return {w: prepared['banks'][w].copy(deep=True) for w in windows}
    try:
        start = processed.report["source_timestamp_min"] - processed.report["time_origin_seconds"]
        if any(t-w*DAY < start for w in windows):
            raise InferenceError("insufficient_past_history: selected history span is incomplete.")
        with snapshot_context(processed_paths(processed), {'dataset_id': dataset_id, 'timestamp': t, 'feature_version': FEATURE_VERSION}) as snapshot:
            identity = frame_identity('asof_features', processed, t, list(windows), min_scan_coverage)
            def produce():
                keys = as_of_candidates(processed, t, dataset_id=dataset_id)
                result = {}
                with bounded_reader(processed, t, max(windows)):
                    for w in windows:
                        frame = snapshot_features(processed, keys, t, w, min_scan_coverage).to_pandas()
                        frame.attrs['history_window_days'] = w
                        result[str(w)] = frame
                return result
            return {int(w): frame for w, frame in SafeCache().get(identity, produce, guard=snapshot.check_live).items()}
    except (OSError, KeyError) as exc:
        raise InferenceError("historical_evidence_missing: restore validated contact/observation files.") from exc


def _read_model_contract(model_directory, *, evidence_path=None):
    """Read native as_of_inference metadata or bind an unchanged T21–T27 study record.

    Study records supply only model identity, feature policy and training/selection
    time bounds. Their cohort, prediction and feature-bank paths are never opened.
    Missing time provenance is a rejection, not a guessed early cutoff.
    """
    directory = Path(model_directory).resolve()
    manifest = read_json(directory/"manifest.json")
    metadata = manifest.get("metadata", {})
    if metadata.get("test_used_for_selection") is True:
        raise InferenceError("model_information_unknown: test-informed selection is not supported by this time provenance.")
    native = metadata.get("as_of_inference")
    if native is not None:
        if native.get("schema_version") != 1 or native.get("feature_contract") != "bounded_window_v1" or native.get("feature_version") != FEATURE_VERSION:
            raise InferenceError("Unsupported as-of model/feature contract version.")
        if native.get("prediction_horizon_hours") != 24:
            raise InferenceError("Only a verified24h target horizon is supported.")
        dataset_id = native.get("dataset_id")
        days = native.get("history_window_days")
        ends = native.get("label_information_ends", {})
        coverage = native.get("min_scan_coverage")
        origin = native.get("time_origin_seconds")
        evidence = "model manifest as_of_inference"
    else:
        if evidence_path is None:
            raise InferenceError("model_information_unknown: verified training/validation/threshold label cutoffs are required.")
        record = read_json(evidence_path)
        if record.get("test_used_for_selection") is True:
            raise InferenceError("model_information_unknown: test-informed selection deadline is unverified.")
        mapping = record.get("model_artifacts", record.get("models", {}))
        matches = [(int(w), name) for w, models in mapping.items() for name, path in models.items()
                   if any((parent/Path(path)).resolve() == directory for parent in (Path.cwd(), *Path(evidence_path).resolve().parents))]
        if len(matches) != 1:
            raise InferenceError("model_evidence_mismatch: selected model is not bound to this record.")
        days, name = matches[0]
        if name != manifest["model_name"]:
            raise InferenceError("Model identity differs from time evidence.")
        if "validation_and_runtime" in record:
            if metadata.get("run_id") != record.get("run_id"):
                raise InferenceError("Model run identity differs from time evidence.")
            summary = record["validation_and_runtime"][str(days)][name]
            if summary["threshold"] != manifest["threshold"] or summary["parameters"] != manifest["parameters"] or summary["feature_columns"] != manifest["feature_columns"]:
                raise InferenceError("Model parameters/threshold/features differ from frozen time evidence.")
            dataset_id = record.get("dataset_id")
            train = summary["training_prediction_times"]
            validation = summary["validation_prediction_times"]
            if record["protocol"].get("future_horizon_hours") != 24:
                raise InferenceError("Only a verified24h target horizon is supported.")
            coverage = record["protocol"]["coverage_threshold"]
            calibrated = record.get("calibration_method")
        else:
            settings = record.get("settings", {})
            if metadata.get("settings") != settings or record.get("scope") != "validation_only":
                raise InferenceError("Model settings differ from selection-time evidence.")
            artifacts = record.get("artifact_hashes", {})
            if artifacts.get(str(directory/"manifest.json")) != sha256(directory/"manifest.json") or artifacts.get(str(directory/"model.joblib")) != manifest["sha256"]:
                raise InferenceError("Model hashes differ from selection-time evidence.")
            dataset_id = NAMESPACES.get(settings.get("dataset"))
            if record["cohort"]["support"]["temporal_split"].get("horizon_hours") != 24:
                raise InferenceError("Only a verified24h target horizon is supported.")
            sets = record["cohort"]["support"]["sets"]
            train, validation = sets["train"]["prediction_times"], sets["validation"]["prediction_times"]
            coverage, calibrated = settings["coverage"], record.get("calibration_method")
        if not train or not validation:
            raise InferenceError("Model training/selection timestamps are missing.")
        train_end = max(_integer(v, "train prediction time") for v in train) + DAY
        validation_end = max(_integer(v, "validation prediction time") for v in validation) + DAY
        ends = {"training_labels_end": train_end, "validation_labels_end": validation_end, "threshold_labels_end": validation_end}
        if calibrated:
            ends["calibration_labels_end"] = validation_end  # Conservative upper bound, never an earlier guessed deadline.
        if "information_deadline" in record:
            ends["declared_selection_end"] = _integer(record["information_deadline"], "declared deadline")
        if (manifest.get("calibration_method") or None) != (calibrated or None):
            raise InferenceError("Calibration provenance differs from model manifest.")
        origin = 0 if dataset_id == "copenhagen" else None
        evidence = str(Path(evidence_path))
    if not isinstance(ends, dict) or not {"training_labels_end", "validation_labels_end", "threshold_labels_end"} <= set(ends):
        raise InferenceError("model_information_unknown: every training/selection label deadline is required.")
    ends = {name: _integer(value, name) for name, value in ends.items()}
    if manifest.get("calibration_method") and "calibration_labels_end" not in ends:
        raise InferenceError("Calibration label deadline is unknown.")
    if dataset_id not in NAMESPACES.values() or type(days) is not int or days not in (1, 3, 7) or days != manifest.get("feature_window_days"):
        raise InferenceError("dataset/window_contract_mismatch: legacy banks or inconsistent windows are unsupported.")
    if not manifest.get("feature_columns") or not set(manifest["feature_columns"]) <= set(WINDOW_FEATURES):
        raise InferenceError("Model feature names are not bounded_window_v1.")
    if coverage is None or not np.isfinite(coverage) or not 0 < coverage <= 1:
        raise InferenceError("Historical feature coverage policy is unknown.")
    origin = _integer(origin, "source time origin")
    if sha256(resolve_path(directory/"model.joblib")) != manifest["sha256"]:
        raise InferenceError("Model artifact checksum changed.")
    return ModelContract(dataset_id, days, ends, float(coverage), origin, manifest["sha256"], manifest.get("calibration_method"), evidence)


def read_model_contract(model_directory, *, evidence_path=None):
    try:
        return _read_model_contract(model_directory, evidence_path=evidence_path)
    except InferenceError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise InferenceError("model_information_unknown: incomplete or invalid model/time provenance.") from exc


def _prospective_guard(processed, timestamp, pair, anchor, now_utc, max_age_seconds):
    if not isinstance(anchor, ClockAnchor) or not isinstance(anchor.reference, str) or not anchor.reference.strip() or not isinstance(anchor.origin_utc, datetime) or anchor.origin_utc.tzinfo is None or anchor.origin_utc.utcoffset() is None:
        raise InferenceError("verified_clock_required: relative Study Days/archive timestamps are not a live wall clock.")
    now = now_utc if now_utc is not None else datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise InferenceError("A timezone-aware current UTC clock is required.")
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, Integral) or not 0 < max_age_seconds <= 3600:
        raise InferenceError("Freshness limit must be1–3600 seconds; archival-scale tolerances are forbidden.")
    origin_utc = anchor.origin_utc.astimezone(timezone.utc)
    prediction_wall_time = origin_utc + timedelta(seconds=timestamp)
    age = (now-prediction_wall_time).total_seconds()
    if not 0 <= age <= max_age_seconds:
        raise InferenceError("stale_or_noncurrent_prediction: use historical_blind_replay for archives.")
    latest = {}
    condition = (ds.field("timestamp") >= timestamp-DAY) & (ds.field("timestamp") < timestamp) & ds.field("user_id").isin(pair)
    try:
        for frame in parquet_frames(processed.directory/"observations.parquet", ["timestamp", "user_id", "scan_observed"], condition):
            frame = frame.loc[frame.scan_observed.eq(True)]
            for user, value in frame.groupby("user_id").timestamp.max().items():
                latest[user] = max(latest.get(user, -1), int(value))
    except OSError as exc:
        raise InferenceError("recent_observations_missing") from exc
    if any(user not in latest or not 0 <= (now-(origin_utc+timedelta(seconds=latest[user]))).total_seconds() <= max_age_seconds for user in pair):
        raise InferenceError("recent_observations_missing: both devices require fresh pre-t observation evidence.")


def _predict_as_of(processed, model_directory, timestamp, a, b, *, dataset_id, history_window_days,
                  mode="historical_blind_replay", evidence_path=None, clock_anchor=None, now_utc=None, max_age_seconds=600):
    """Blind/realtime inference; never opens label tables, stored cohorts or evaluation banks."""
    t = _integer(timestamp, "timestamp")
    pair = _pair(a, b)
    _source(processed, dataset_id)
    if mode not in MODES:
        raise InferenceError("Unsupported inference mode.")
    contract = read_model_contract(model_directory, evidence_path=evidence_path)
    if contract.dataset_id != dataset_id or type(history_window_days) is not int or history_window_days != contract.history_window_days:
        raise InferenceError("dataset/window_contract_mismatch")
    if contract.time_origin_seconds != processed.report.get("time_origin_seconds"):
        raise InferenceError("Source/model relative-time origins differ.")
    if t <= contract.information_deadline:
        raise InferenceError("model_information_conflict: model used training/selection labels at or after t.")
    if not processed.report.get("scan_coverage_available"):
        raise InferenceError("historical_scan_evidence_missing: observation availability is unknown.")
    if mode == "prospective_inference":
        _prospective_guard(processed, t, pair, clock_anchor, now_utc, max_age_seconds)
    frames = as_of_features(processed, t, dataset_id=dataset_id, windows=(history_window_days,), min_scan_coverage=contract.min_scan_coverage)
    frame = frames[history_window_days]
    row = frame.loc[frame.user_min.eq(pair[0]) & frame.user_max.eq(pair[1])]
    if len(row) != 1:
        raise InferenceError("unknown_historical_pair: no contact for this pair in[t-1d,t).")
    scans = row[["scan_coverage_a", "scan_coverage_b"]].to_numpy(dtype=float)
    if not np.isfinite(scans).all() or (scans <= 0).any():
        raise InferenceError("historical_scan_evidence_missing: both endpoints require pre-t scan evidence.")
    X = row.loc[:, WINDOW_FEATURES].copy()
    X.attrs["history_window_days"] = history_window_days
    from src.readonly_models import load_model
    model = load_model(model_directory)
    base = getattr(model, "base", model)
    if getattr(base, "feature_contract", None) != "bounded_window_v1" or model.feature_window_days != history_window_days or getattr(model, "method", None) != contract.calibration_method:
        raise InferenceError("Loaded model feature/window contract differs.")
    return {"mode": mode, "dataset_id": dataset_id, "timestamp": t, "pair": list(pair), "history_window_days": history_window_days,
            "probability": float(model.predict_proba(X)[0, 1]), "threshold": float(model.threshold),
            "information_deadline": contract.information_deadline, "label_information_ends": dict(contract.label_information_ends),
            "historical_features": X.iloc[0].to_dict(), "candidate_policy": "[t-1d,t) contacts only",
            "observation_note": "Positive historical scan evidence is required; partial coverage is not continuous device presence."}


def predict_as_of(processed, model_directory, timestamp, a, b, *, dataset_id, history_window_days,
                  mode='historical_blind_replay', evidence_path=None, clock_anchor=None, now_utc=None, max_age_seconds=600):
    with snapshot_context(processed_paths(processed)+model_paths(model_directory, evidence_path),
                          {'dataset_id': dataset_id, 'timestamp': int(timestamp), 'protocol': 'T28/T32-stable-archive'}):
        return _predict_as_of(processed, model_directory, timestamp, a, b, dataset_id=dataset_id, history_window_days=history_window_days,
                              mode=mode, evidence_path=evidence_path, clock_anchor=clock_anchor, now_utc=now_utc, max_age_seconds=max_age_seconds)


def reveal_outcome(processed, timestamp, a, b, *, backtest=False, min_scan_coverage=0.5):
    """Separate authorized reveal using raw future contacts and unique observed scan bins.

    It never decides membership in the inference population. A positive observation
    is sufficient evidence; an absent event requires a complete and covered horizon.
    """
    if backtest is not True:
        raise InferenceError("explicit_backtest_required: outcomes are separate from blind inference.")
    t, pair = _integer(timestamp, "timestamp"), _pair(a, b)
    if not np.isfinite(min_scan_coverage) or not 0 < min_scan_coverage <= 1:
        raise InferenceError("Coverage threshold must be in (0,1].")
    expression = (ds.field("timestamp") > t) & (ds.field("timestamp") <= t+DAY)
    for frame in parquet_frames(processed.directory/"contacts.parquet", ["timestamp"], expression & (ds.field("user_min") == pair[0]) & (ds.field("user_max") == pair[1])):
        if len(frame):
            return {"outcome": "Contact", "label_24h": 1, "reason": "observed_positive_evidence"}
    end = processed.report["source_timestamp_max"] - processed.report["time_origin_seconds"]
    if t+DAY > end:
        return {"outcome": "Unknown", "label_24h": None, "reason": "future_window_incomplete"}
    if processed.report.get("dataset") != "Copenhagen" or not processed.report.get("scan_coverage_available"):
        return {"outcome": "Unknown", "label_24h": None, "reason": "scan_coverage_unknown"}
    bins = {user: set() for user in pair}
    try:
        for frame in parquet_frames(processed.directory/"observations.parquet", ["timestamp", "user_id", "scan_observed"], expression & ds.field("user_id").isin(pair)):
            frame = frame.loc[frame.scan_observed.eq(True)]
            for timestamp_value, user, _ in frame.itertuples(index=False, name=None):
                bins[user].add(int(timestamp_value)//300)
    except OSError:
        return {"outcome": "Unknown", "label_24h": None, "reason": "scan_evidence_missing"}
    coverage = {str(user): len(bins[user])/288 for user in pair}
    if min(coverage.values()) < min_scan_coverage:
        return {"outcome": "Unknown", "label_24h": None, "reason": "low_scan_coverage", "coverage": coverage}
    return {"outcome": "No Contact", "label_24h": 0, "reason": "adequately_observed_no_contact", "coverage": coverage}

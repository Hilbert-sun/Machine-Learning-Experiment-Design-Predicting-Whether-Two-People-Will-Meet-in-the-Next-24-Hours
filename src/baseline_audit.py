"""T18: freeze and verify existing T17 evidence without refitting or replacing it."""

import hashlib
import json
from pathlib import Path
import subprocess

import pandas as pd

from src.temporal_split import chronological_split


def sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def immutable_json(path, value):
    path = Path(path)
    payload = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text() != payload:
            raise ValueError(f"Frozen manifest differs: {path.name}; preserve it and use a new version.")
    else:
        with path.open("x") as handle:
            handle.write(payload)
    return path


def freeze_t17(root):
    root = Path(root).resolve()
    safe = json.loads((root / "reports/T17_SAFE_METADATA.json").read_text())
    record = json.loads((root / safe["private_training_reports"][0]).read_text())
    labels_path = Path(record["provenance"]["input_signatures"][0]["path"])
    labels = pd.read_parquet(labels_path)
    eligible = labels.loc[labels.eligible_for_evaluation & labels.label_24h.notna()].copy()
    eligible.attrs.update(source_rows=len(labels), excluded_rows=len(labels)-len(eligible))
    split = chronological_split(eligible)
    assert split.report == record["split"]
    parts = {name: getattr(split, name) for name in ("train", "validation", "test")}
    purged = eligible.loc[
        ((eligible.timestamp < split.report["validation_start"]) & (eligible.timestamp + 86400 >= split.report["validation_start"])) |
        ((eligible.timestamp >= split.report["validation_start"]) & (eligible.timestamp < split.report["test_start"]) & (eligible.timestamp + 86400 >= split.report["test_start"]))]
    purge_counts = [{"timestamp": int(t), "study_day": int(t // 86400 + 1), "rows": len(g),
                     "positive": int(g.label_24h.eq(1).sum()), "negative": int(g.label_24h.eq(0).sum()),
                     "reason": "inclusive_24h_label_window_reaches_validation" if t < split.report["validation_start"] else "inclusive_24h_label_window_reaches_test"}
                    for t, g in purged.groupby("timestamp")]
    assert len(eligible) == sum(len(p) for p in parts.values()) + len(purged) == 769627
    assert len(purged) == safe["purged_rows"] == 84332
    files = ["reports/T17_DATA_DIAGNOSTICS.md", "reports/T17_REAL_EXPERIMENT.md", "reports/T17_METRICS.csv", "reports/T17_METRICS.json", "reports/T17_SAFE_METADATA.json"]
    files += safe["private_training_reports"]
    files += [str(Path(x["path"]).relative_to(root)) for x in record["provenance"]["input_signatures"]]
    files += [x["source_path"] for x in safe["datasets"] if "sha256" in x]
    files += [str(Path(p) / suffix) for p in safe["model_artifacts"].values() for suffix in ("manifest.json", "model.joblib")]
    for item in safe["datasets"]:
        if "sha256" in item:
            assert sha256(root / item["source_path"]) == item["sha256"]
    commit = subprocess.check_output(["git", "rev-parse", "f116951^{commit}"], cwd=root, text=True).strip()
    for path, expected in safe["code_hashes"].items():
        assert hashlib.sha256(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=root)).hexdigest() == expected
    manifest = {"schema_version": 1, "baseline": "T17", "baseline_commit": commit,
                "protocol": safe["protocol"], "metrics": safe["metrics"], "calibration": safe["calibration"],
                "dataset_sources": [{k: d[k] for k in ("dataset", "source_path", "sha256", "bytes")} for d in safe["datasets"] if "sha256" in d],
                "file_hashes": {p: sha256(root / p) for p in files}, "code_hashes_at_baseline_commit": safe["code_hashes"],
                "model_paths": safe["model_artifacts"], "eligible_rows": len(eligible), "coverage_excluded_rows": len(labels)-len(eligible),
                "coverage_exclusion_reasons": labels.loc[~labels.eligible_for_evaluation].exclusion_reason.value_counts().to_dict(),
                "purged_rows": len(purged), "purge_by_day": purge_counts,
                "splits": {name: {"rows": len(p), "positive": int(p.label_24h.eq(1).sum()), "negative": int(p.label_24h.eq(0).sum()),
                                  "prediction_times": sorted(int(t) for t in p.timestamp.unique()), "independent_prediction_days": p.timestamp.nunique()}
                           for name, p in parts.items()},
                "remaining_risks": ["T17 test days were already inspected; new same-source comparisons are not a pristine independent holdout.",
                                    "Symmetrized recorded scan bins are an availability proxy, not proof of continuous presence.",
                                    "Repeated pairs/participants and few independent prediction days limit inference."]}
    return immutable_json(root / "reports/window_study/T18_BASELINE_MANIFEST.json", manifest)


def verify_frozen(root, manifest):
    root = Path(root)
    record = json.loads(Path(manifest).read_text())
    for name, expected in record["file_hashes"].items():
        if sha256(root / name) != expected:
            raise ValueError(f"T17 baseline artifact changed: {name}")
    return True


if __name__ == "__main__":
    path = freeze_t17(Path.cwd())
    verify_frozen(Path.cwd(), path)
    print(path)

"""Read-only T18–T22 artifact/metric verification; never fits or selects models."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.baseline_audit import sha256, verify_frozen
from src.model_registry import ModelRegistry
from src.window_study import read_inputs, model_input, verify_exported_metrics


def verify_study(root):
    root = Path(root)
    public = root/"reports/window_study"
    primary = json.loads((public/"T21_RESULTS.json").read_text())
    directory = public/primary["run_id"]
    frozen = json.loads((directory/"PROTOCOL_FROZEN.json").read_text())
    for path, expected in frozen["code_hashes"].items():
        if sha256(root/path) != expected:
            raise ValueError(f"Frozen statistical code changed: {path}")
    second = json.loads((directory/"T22_PROTOCOL_FROZEN.json").read_text())
    if sha256(root/"src/window_robustness.py") != second["implementation_sha256"]:
        raise ValueError("Frozen T22 implementation changed.")
    if sha256(directory/"PROTOCOL_FROZEN.json") != second["parent_protocol_sha256"] or sha256(directory/"T21_RESULTS.json") != second["parent_results_sha256"]:
        raise ValueError("T21 frozen evidence changed.")
    robust = json.loads((directory/"T22_ROBUSTNESS.json").read_text())
    assert primary == json.loads((directory/"T21_RESULTS.json").read_text())
    assert robust == json.loads((public/"T22_ROBUSTNESS.json").read_text())
    assert robust["primary_results_preserved_sha256"] == sha256(directory/"T21_RESULTS.json")
    _, banks, _, _ = read_inputs(root)
    stages = ["T21","T22"] + [f"T22_fold{f['study_day']}" for f in robust["walk_forward_folds"] if f["status"]=="ready"]
    model_count = 0
    for stage in stages:
        verify_exported_metrics(directory,stage)
        record = json.loads((directory/f"{stage}_RESULTS.json").read_text())
        model_frozen = json.loads((directory/f"{stage}_MODELS_FROZEN.json").read_text())
        frozen_paths = model_frozen["model_artifacts"]
        # T22 freezes a single3d bank; primary and fold manifests freeze multiple banks.
        if frozen_paths and all(isinstance(p,str) for p in frozen_paths.values()):
            assert len(record["model_artifacts"]) == 1
            frozen_paths = {next(iter(record["model_artifacts"])):frozen_paths}
        assert record["model_artifacts"] == frozen_paths
        for window, prediction in record["predictions_local_ignored"].items():
            frame = pd.read_parquet(directory/prediction["filename"])
            X = model_input(banks[int(window)],frame,int(window))
            for name, relative in record["model_artifacts"][window].items():
                model = ModelRegistry.load(root/relative)
                assert model.threshold == float(frame[f"threshold_{name}"].iloc[0])
                np.testing.assert_allclose(model.predict_proba(X)[:,1],frame[f"p_{name}"],rtol=1e-12,atol=1e-12)
                model_count += 1
    assert verify_frozen(root,public/"T18_BASELINE_MANIFEST.json")
    return {"run_id":primary["run_id"],"stages_verified":len(stages),"saved_models_full_prediction_equivalence":model_count,
            "metric_recomputation":"passed","T17_unchanged":True,"statistical_source_freeze":"passed"}


if __name__ == "__main__":
    print(json.dumps(verify_study(Path.cwd()),indent=2))

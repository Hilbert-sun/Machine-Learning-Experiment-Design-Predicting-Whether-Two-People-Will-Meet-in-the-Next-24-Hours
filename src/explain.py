"""Native TreeSHAP on raw margins, or explicitly non-SHAP local sensitivity."""

import numpy as np
import pandas as pd

from src.feature_policy import feature_window_view


def native_tree_shap(model, X):
    base = getattr(model, "base", model)
    if base.name not in {"xgboost", "lightgbm"}:
        return None
    pipeline = base.estimator
    view = feature_window_view(X, base.feature_window_days).loc[:, base.feature_columns]
    transformed = pipeline[:-1].transform(view)
    names = list(pipeline[:-1].get_feature_names_out())
    classifier = pipeline.named_steps["classifier"]
    if base.name == "xgboost":
        from xgboost import DMatrix
        matrix = DMatrix(transformed)
        contributions = classifier.get_booster().predict(matrix, pred_contribs=True)
        margin = classifier.get_booster().predict(matrix, output_margin=True)
    else:
        contributions = classifier.booster_.predict(transformed, pred_contrib=True)
        margin = classifier.booster_.predict(transformed, raw_score=True)
    contributions = np.asarray(contributions)
    if not np.allclose(contributions.sum(axis=1), margin, atol=1e-4):
        raise RuntimeError("原生SHAP贡献与模型原始分数不一致。")
    return {"values": contributions[:, :-1], "bias": contributions[:, -1], "feature_names": names,
            "scale": "base_model_raw_margin", "raw_margin": np.asarray(margin)}


def local_explanation(model, X, *, limit=10):
    native = native_tree_shap(model, X)
    if native is not None:
        rows = pd.DataFrame({"feature": native["feature_names"], "contribution": native["values"][0]})
        method, scale = "native_tree_shap", native["scale"]
    else:
        base = getattr(model, "base", model)
        reference = getattr(base, "feature_reference", {})
        probability = float(model.predict_proba(X)[0, 1])
        records = []
        for feature in base.feature_columns:
            if feature in reference:
                changed = X.copy()
                changed[feature] = reference[feature]
                records.append({"feature": feature, "contribution": probability - float(model.predict_proba(changed)[0, 1])})
        rows = pd.DataFrame(records, columns=["feature", "contribution"])
        method, scale = "training_median_replacement_sensitivity", "probability_change_not_shap"
    rows = rows.iloc[np.argsort(-rows.contribution.abs().to_numpy())].head(limit)
    return {"method": method, "scale": scale, "rows": rows.to_dict(orient="records")}

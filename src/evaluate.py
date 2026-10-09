"""Binary validation metrics and a validation-only F1 threshold selector."""

import numpy as np
from sklearn.metrics import (
    accuracy_score, average_precision_score, brier_score_loss, f1_score,
    log_loss, precision_recall_curve, precision_score, recall_score, roc_auc_score,
)


def _checked(y, probabilities):
    y, probabilities = np.asarray(y), np.asarray(probabilities, dtype=float)
    if len(y) == 0 or y.shape != probabilities.shape or not np.isin(y, [0, 1]).all():
        raise ValueError("评估需要非空、对齐的二元目标和概率。")
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("概率必须为 [0,1] 的有限数值。")
    return y.astype(int), probabilities


def binary_metrics(y, probabilities, *, threshold=0.5):
    y, probabilities = _checked(y, probabilities)
    prediction = probabilities >= threshold
    two_classes = len(np.unique(y)) == 2
    return {
        "rows": len(y), "positive_rate": float(y.mean()), "threshold": float(threshold),
        "pr_auc_average_precision": float(average_precision_score(y, probabilities)) if y.any() else None,
        "brier_score": float(brier_score_loss(y, probabilities)),
        "log_loss": float(log_loss(y, probabilities, labels=[0, 1])),
        "precision": float(precision_score(y, prediction, zero_division=0)),
        "recall": float(recall_score(y, prediction, zero_division=0)),
        "f1": float(f1_score(y, prediction, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, probabilities)) if two_classes else None,
        "accuracy": float(accuracy_score(y, prediction)),
    }


def choose_threshold(y, probabilities):
    y, probabilities = _checked(y, probabilities)
    if not y.any():
        return 0.5
    precision, recall, thresholds = precision_recall_curve(y, probabilities)
    score = np.divide(2 * precision[:-1] * recall[:-1], precision[:-1] + recall[:-1], out=np.zeros_like(thresholds), where=precision[:-1] + recall[:-1] > 0)
    best = np.flatnonzero(np.isclose(score, score.max()))
    return float(thresholds[best[np.argmin(abs(thresholds[best] - 0.5))]])

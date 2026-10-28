"""Play "research reference": a public aggregate re-contact table from the Copenhagen study.

The builder reads local T07 labels and T08 features once and writes a small suppressed aggregate JSON.
Play itself only reads that reviewed JSON; it never touches datasets or models, and the fixed-rule
entertainment index is unchanged. The reference describes study pairs, not the user's probability.
"""

import argparse
import json
from pathlib import Path

import numpy as np

DAY = 86400
TABLE = Path(__file__).resolve().parents[1] / "studies/play_reference/PLAY_REFERENCE.json"
RECENCY = {"day": (0, DAY), "week": (DAY, 7*DAY), "month": (7*DAY, 30*DAY)}
FREQUENCY = {"zero": (0, 0), "one_two": (1, 2), "three_five": (3, 5), "six_plus": (6, 14)}
RECENCY_TEXT = {"day": "24 小时内", "week": "1–7 天前", "month": "7 天以前"}
FREQUENCY_TEXT = {"zero": "没有", "one_two": "1–2 天", "three_five": "3–5 天", "six_plus": "6 天及以上"}
SUPPRESSION = {"minimum_samples": 200, "minimum_each_class": 20}
PROTOCOL = {
    "version": 1, "task": "PLAY-REF", "dataset_id": "copenhagen",
    "population": "T07 coverage-eligible labels of all previously contacted pairs, prediction times with complete 14-day history",
    "recency": "hours since the last contact before t; questionnaire 最近24小时/最近7天/最近30天 map to <1d, 1–7d, ≥7d",
    "frequency": "distinct contact days in [t-14d, t) as an approximation of the questionnaire's 30-day encounter count",
    "outcome": "share with a recorded contact in (t, t+24h]; Unknown labels excluded upstream",
    "suppression": SUPPRESSION, "fitting": False, "selection": False,
    "limits": "Danish students' Bluetooth proximity in one month of 2013; self-reported coarse answers only loosely match these buckets",
}


def build(root):
    import pandas as pd
    root = Path(root)
    labels = pd.read_parquet(sorted((root/"data/processed/labels").glob("labels-*.parquet"))[0],
                             columns=["timestamp", "user_min", "user_max", "label_24h", "eligible_for_evaluation"])
    columns = ["timestamp", "user_min", "user_max", "time_since_last_contact", "unique_contact_days_14d", "history_complete_14d"]
    features = next(frame for frame in (pd.read_parquet(p) for p in sorted((root/"data/features").glob("features-*.parquet")))
                    if set(columns) <= set(frame.columns))[columns]
    frame = labels.merge(features, on=["timestamp", "user_min", "user_max"], validate="one_to_one")
    frame = frame.loc[frame.eligible_for_evaluation & frame.history_complete_14d.astype(bool) & frame.label_24h.notna()]
    cells = []
    for recency, (low, high) in RECENCY.items():
        for frequency, (fewest, most) in FREQUENCY.items():
            part = frame.loc[frame.time_since_last_contact.ge(low) & frame.time_since_last_contact.lt(high)
                             & frame.unique_contact_days_14d.between(fewest, most)]
            positive = int(part.label_24h.sum()); negative = len(part) - positive
            shown = len(part) >= SUPPRESSION["minimum_samples"] and min(positive, negative) >= SUPPRESSION["minimum_each_class"]
            cells.append({"recency": recency, "frequency": frequency, "samples": len(part) if shown else None,
                          "recontact_rate": round(positive/len(part), 3) if shown else None, "suppressed": not shown})
    return {"protocol": PROTOCOL, "eligible_samples": len(frame), "prediction_times": int(frame.timestamp.nunique()),
            "overall_recontact_rate": round(float(frame.label_24h.mean()), 3), "cells": cells}


def reference(recency, frequency, table=None):
    """Return the study reference for coarse answers, or a reason when none can be shown."""
    table = table or json.loads(TABLE.read_text())
    if recency not in RECENCY or frequency not in FREQUENCY:
        return {"status": "unavailable",
                "reason": "研究只覆盖 28 天内的接触记录；填写“最近一次偶遇”（30 天内）和“过去 30 天次数”后才能对照。"}
    cell = next(c for c in table["cells"] if c["recency"] == recency and c["frequency"] == frequency)
    if cell["suppressed"]:
        return {"status": "suppressed", "reason": "研究里与你们情况类似的配对太少，为保护隐私不显示比例。"}
    return {"status": "ready", "rate": cell["recontact_rate"], "samples": cell["samples"],
            "recency_text": RECENCY_TEXT[recency], "frequency_text": FREQUENCY_TEXT[frequency],
            "overall_rate": table["overall_recontact_rate"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = build(args.root)
    target = args.root/"studies/play_reference/PLAY_REFERENCE.json"
    if args.verify_only:
        assert json.loads(target.read_text()) == json.loads(json.dumps(result)), "Public Play reference differs from recomputation."
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result["cells"], ensure_ascii=False, indent=1), result["eligible_samples"], result["overall_recontact_rate"])


if __name__ == "__main__":
    main()

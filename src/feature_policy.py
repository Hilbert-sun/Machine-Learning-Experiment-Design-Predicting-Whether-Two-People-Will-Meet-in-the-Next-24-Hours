"""Consistent bounded-history feature groups for fitting and inference."""

import re
import numpy as np


def feature_window_view(frame, days=None):
    result = frame.copy()
    if days is None:  # Preserve the original full-bank model contract.
        return result
    if days not in (1, 3, 7, 14):
        raise ValueError("模型历史窗口必须为1/3/7/14天。")
    for name in result.columns:
        suffix = re.search(r"_(\d+)d$", name)
        required = int(suffix.group(1)) if suffix else 14 if name == "historical_contact_probability" else 7 if name in {
            "common_neighbors_historical", "historical_network_degree_a", "historical_network_degree_b", "scan_coverage_a", "scan_coverage_b",
        } else 0
        if required > days:
            result[name] = np.nan
    if "time_since_last_contact" in result:
        result.loc[result.time_since_last_contact > days * 86400, "time_since_last_contact"] = np.nan
    return result

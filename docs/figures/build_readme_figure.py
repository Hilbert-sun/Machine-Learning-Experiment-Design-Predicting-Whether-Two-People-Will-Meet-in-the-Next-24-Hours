"""Build the README result figure from the public T35/T37 aggregates (no private data).

Run: python docs/figures/build_readme_figure.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("rolling_ap.svg")
WIDTH, LABEL_W, BAR_X1, BAR_H, ROW = 720, 150, 640, 18, 30
X_MAX = 0.8


def x(value):
    return LABEL_W + value / X_MAX * (BAR_X1 - LABEL_W)


def bar(y, value):
    # Square at the baseline, 4px rounded data end.
    x0, x1, r = LABEL_W, x(value), 4
    return (f'<path class="bar" d="M{x0:.1f},{y:.1f}H{x1-r:.1f}Q{x1:.1f},{y:.1f} {x1:.1f},{y+r:.1f}'
            f'V{y+BAR_H-r:.1f}Q{x1:.1f},{y+BAR_H:.1f} {x1-r:.1f},{y+BAR_H:.1f}H{x0:.1f}Z"><title>{value:.3f}</title></path>')


def panel(top, title, rows, prevalence):
    parts = [f'<text class="title" x="0" y="{top}">{title}</text>']
    first = top + 16
    bottom = first + len(rows) * ROW - (ROW - BAR_H)
    px = x(prevalence)
    # Reference line sits behind the bars and shows through the gaps.
    parts.append(f'<line class="ref" x1="{px:.1f}" x2="{px:.1f}" y1="{first-4}" y2="{bottom+4}"/>')
    for i, (label, value) in enumerate(rows):
        y = first + i * ROW
        parts.append(f'<text class="label" x="{LABEL_W-10}" y="{y+BAR_H/2+4:.1f}" text-anchor="end">{label}</text>')
        parts.append(bar(y, value))
        parts.append(f'<text class="value" x="{x(value)+6:.1f}" y="{y+BAR_H/2+4:.1f}">{value:.3f}</text>')
    parts.append(f'<line class="axis" x1="{LABEL_W}" x2="{LABEL_W}" y1="{first-4}" y2="{bottom+4}"/>')
    return parts, bottom


def main():
    t35 = json.loads((ROOT/"studies/rolling_validation/T35_RESULTS.json").read_text())
    t37 = json.loads((ROOT/"studies/hawkes_features/T37_RESULTS.json").read_text())
    ap35 = {(m["window_days"], m["model"]): m["pr_auc_average_precision"] for m in t35["metrics"]}
    ap37 = {m["model"]: m["pr_auc_average_precision"] for m in t37["metrics"]}
    prevalence = t35["metrics"][0]["positive_rate"]
    assert all(abs(m["positive_rate"] - prevalence) < 1e-12 for m in t35["metrics"] + t37["metrics"])
    a, a_bottom = panel(18, "历史越长越准：XGBoost 合并 AP", [(f"{d} 天历史", ap35[(d, "xgboost")]) for d in (1, 3, 7)], prevalence)
    b_rows = [("XGBoost + Hawkes", ap37["xgboost_hawkes"]), ("XGBoost", ap37["xgboost"]), ("Hawkes（无标签）", ap37["hawkes"]),
              ("Logistic", ap37["logistic_regression"]), ("历史频率", ap35[(7, "historical_frequency")])]
    b, b_bottom = panel(a_bottom + 44, "7 天历史下的模型对比：合并 AP", b_rows, prevalence)
    note_y = b_bottom + 28
    note = (f'<text class="note" x="{x(prevalence)+4:.1f}" y="{note_y-12}">虚线 = 随机排序（正例率 {prevalence:.3f}）</text>'
            f'<text class="note" x="0" y="{note_y+6}">Copenhagen · T35 滚动起点 · 11 个测试日 · {t35["metrics"][0]["rows"]:,} 个样本；测试日此前均被评估过，结果为描述性。</text>')
    height = note_y + 16
    style = """
  .bar{fill:#2a78d6}.title{font-weight:600;font-size:14px;fill:#0b0b0b}.label,.value{font-size:12px;fill:#52514e}
  .value{fill:#0b0b0b}.note{font-size:11px;fill:#52514e}.ref{stroke:#52514e;stroke-dasharray:3 3;stroke-width:1}
  .axis{stroke:#c3c2b7;stroke-width:1}text{font-family:system-ui,-apple-system,"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif}
  .bg{fill:#fcfcfb}
  @media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.bar{fill:#3987e5}.title,.value{fill:#f0efec}.label,.note{fill:#c3c2b7}
  .ref{stroke:#c3c2b7}.axis{stroke:#52514e}}"""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-16 -8 {WIDTH+32} {height+16}" width="{WIDTH+32}" role="img" '
           f'aria-label="滚动验证合并 AP：XGBoost 1/3/7 天及 7 天模型对比">\n<style>{style}\n</style>\n'
           f'<rect class="bg" x="-16" y="-8" width="{WIDTH+32}" height="{height+16}" rx="8"/>\n'
           + "\n".join(a + b) + "\n" + note + "\n</svg>\n")
    OUT.write_text(svg)
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

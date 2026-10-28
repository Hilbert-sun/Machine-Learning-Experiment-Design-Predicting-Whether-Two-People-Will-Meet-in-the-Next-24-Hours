"""Build report v2: the frozen REPORT-FULL text plus a T35–T40 chapter from public study aggregates.

v1 (deliverables/Encounter_Lab_Full_Report.md, baseline 478a320) is read, never written. Every number in
the new chapter comes from studies/*/T3x_RESULTS.json and is asserted here. Requires the separate
document environment (reportlab, pypdf, pdfplumber, Pillow); PDF and renders stay local.
"""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Line, Rect
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[2]
V2 = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_report", ROOT/"deliverables/build_report.py")
br = importlib.util.module_from_spec(spec); spec.loader.exec_module(br)
import reportlab.platypus.paragraph as rl_paragraph
# Full-width Chinese punctuation may not start a line: let it hang into the 12pt right guard instead.
import reportlab.lib.textsplit as rl_textsplit
_PUNCT = "\uff0c\uff1b\uff1a\uff01\uff1f\uff05\u300b\u201d\u2019"
rl_paragraph.ALL_CANNOT_START += _PUNCT
rl_textsplit.ALL_CANNOT_START += _PUNCT  # single-fragment paragraphs wrap through textsplit.wordSplit
import inspect
# When a Latin run overflows, reportlab backtracks to a CJK split point without checking the next glyph;
# also refuse split points that would start the next line with forbidden punctuation.
_source = inspect.getsource(rl_paragraph.cjkFragSplit)
_old = "if uj and category(uj)=='Zs' or ord(uj)>=0x3000:"
assert _source.count(_old) == 1
exec(compile(_source.replace(_old, "if (uj and category(uj)=='Zs' or ord(uj)>=0x3000) and (j+1>=nU or U[j+1] not in ALL_CANNOT_START):"),
             rl_paragraph.__file__, "exec"), rl_paragraph.__dict__)
STUDIES = {name: ROOT/f"studies/{folder}/{name}_RESULTS.json" for name, folder in
           (("T35", "rolling_validation"), ("T36", "hawkes_baseline"), ("T37", "hawkes_features"),
            ("T38", "participant_holdout"), ("T39", "day_analysis"), ("T40", "hawkes_short"))}
MD = V2/"Encounter_Lab_Full_Report_v2.md"
PDF = V2/"Encounter_Lab_Full_Report_v2.pdf"
NAMES = {**br.NAMES, "hawkes": "Hawkes（无标签）", "hawkes_wide": "Hawkes扩展网格", "xgboost_hawkes": "XGBoost+Hawkes特征",
         "xgboost_holdout": "XGBoost（仅A–A训练）", "logistic_regression_holdout": "逻辑回归（仅A–A训练）",
         "historical_frequency_holdout": "历史频率（仅A–A）"}
REFERENCES = [
    "[22] TASHMAN L J. Out-of-sample tests of forecasting accuracy: an analysis and review[J]. International Journal of Forecasting, 2000, 16(4):437-450. DOI:10.1016/S0169-2070(00)00065-0.",
    "[23] HAWKES A G. Spectra of some self-exciting and mutually exciting point processes[J]. Biometrika, 1971, 58(1):83-90. DOI:10.1093/biomet/58.1.83.",
    "[24] ENCOUNTER LAB. T35–T40补充研究公开聚合结果：studies/目录[EB/OL]. research-v2.2, 2026-10-28. https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/tree/research-v2.2/studies.",
]
COVER = ("完整项目研究报告（第二版）", "编制日期：2026年10月28日", "研究与工程基准：research-v2.2，第一版478a320，补充至T40",
         "涵盖T01-T40与P01-P03", "依据公开源码、冻结聚合材料、补充研究公开结果与实际CI记录编写")


def f3(v): return f"{v:.3f}"
def f4(v): return f"{v:.4f}"
def signed(v): return f"{v:+.3f}"
def ci(v): return "[" + ", ".join(f"{x:.3f}" for x in v) + "]"


def load():
    return {k: json.loads(p.read_text()) for k, p in STUDIES.items()}


def metric(result, model, window=7):
    return next(m for m in result["metrics"] if m["model"] == model and m["window_days"] == window)


def contrast(result, name):
    return next(c for c in result["contrasts"] if c["contrast"] == name)


def chapter(data):
    t35, t36, t37, t38, t39, t40 = (data[k] for k in ("T35", "T36", "T37", "T38", "T39", "T40"))
    cols = ("pr_auc_average_precision", "roc_auc", "brier_score", "ndcg_at_5", "precision_at_5")
    head = ["窗口", "模型", "合并AP", "ROC-AUC", "Brier", "NDCG@5", "P@5"]
    rows35 = [[f"{w}天", NAMES[m]] + [f4(metric(t35, m, w)[c]) for c in cols]
              for w, m in ((1, "xgboost"), (3, "xgboost"), (7, "xgboost"), (7, "logistic_regression"), (7, "historical_frequency"))]
    rows_h = [["7天", NAMES[m]] + [f4(metric(src, m)[c]) for c in cols]
              for src, m in ((t37, "xgboost_hawkes"), (t35, "xgboost"), (t36, "hawkes"), (t40, "hawkes_wide"))]
    across = {(r["population"], r["model"]): r for r in t38["across_partitions"] if "model" in r}
    rows38 = [[NAMES[m] if m in NAMES else m, f4(across[("unseen_both", m)]["pr_auc_average_precision_mean"]),
               f"{across[('unseen_both', m)]['pr_auc_average_precision_min']:.4f}–{across[('unseen_both', m)]['pr_auc_average_precision_max']:.4f}",
               f4(across[("unseen_both", m)]["roc_auc_mean"]), f4(across[("unseen_both", m)]["ndcg_at_5_mean"])]
              for m in ("xgboost_holdout", "xgboost", "hawkes", "logistic_regression_holdout", "historical_frequency_holdout")]
    NAMES.setdefault("xgboost", "XGBoost")
    rows38[1][0] = "XGBoost（见过全部参与者）"
    d71 = contrast(t35, "7d xgboost - 1d xgboost")
    assert d71["days_positive"] == 11 and contrast(t35, "7d xgboost - 7d logistic_regression")["days_positive"] == 9
    rho = {(c["target"], c["descriptor"]): c["spearman_rho"] for c in t39["correlations"]}
    holdout_ap = across[("unseen_both", "xgboost_holdout")]["pr_auc_average_precision_mean"]
    seen_ap = across[("unseen_both", "xgboost")]["pr_auc_average_precision_mean"]
    gaps = next(r for r in t38["across_partitions"] if r.get("contrast") == "7d xgboost_holdout - 7d hawkes" and r["population"] == "unseen_both")
    assert all(0.010 <= g <= 0.025 for g in [round(x, 3) for x in gaps["pooled_delta_ap_by_salt"]]) and gaps["intervals_excluding_zero"] == 0
    assert [s["selected_half_life_minutes"] for s in t40["fold_selections"]].count(5) == 0
    assert metric(t35, "xgboost")["test_days"] == 11 and metric(t35, "xgboost")["rows"] == 59140
    assert abs(metric(t35, "xgboost")["positive_rate"] - 0.1966) < 5e-5
    days = t39["per_day"]; low = min(days, key=lambda d: d["positive_rate"])
    assert abs(low["positive_rate"] - 0.054) < 5e-4 and low["lift_xgboost"] == max(d["lift_xgboost"] for d in days)
    values = {
        "T35_TABLE": br.table(head, rows35), "HAWKES_TABLE": br.table(head, rows_h),
        "HOLDOUT_TABLE": br.table(["模型", "合并AP均值", "5种划分范围", "ROC-AUC", "NDCG@5"], rows38),
        "D71": signed(d71["pooled_delta_ap"]), "D71_CI": ci(d71["confidence_interval_95"]),
        "DLR": signed(contrast(t35, "7d xgboost - 7d logistic_regression")["pooled_delta_ap"]),
        "PARITY": f"{max(t40['t36_parity_max_abs'].values()):.1e}",
        "HAWKES_AP": f3(metric(t36, "hawkes")["pr_auc_average_precision"]),
        "XGB_HAWKES": f3(contrast(t36, "7d xgboost - 7d hawkes")["pooled_delta_ap"]),
        "WIDE_AP": f3(metric(t40, "hawkes_wide")["pr_auc_average_precision"]),
        "T37_DELTA": f3(contrast(t37, "7d xgboost_hawkes - 7d xgboost")["pooled_delta_ap"]),
        "HOLDOUT_AP": f3(holdout_ap), "HOLDOUT_GAP": f3(seen_ap - holdout_ap),
        "DAY_MIN": f"{t39['summary']['ap_xgboost_range'][0]:.2f}", "DAY_MAX": f"{t39['summary']['ap_xgboost_range'][1]:.2f}",
        "RHO_PREV": f"{rho[('ap_xgboost', 'positive_rate')]:+.2f}", "RHO_REC": f"{rho[('ap_xgboost', 'mean_recency_hours')]:+.2f}",
        "LIFT_MAX": f"{low['lift_xgboost']:.1f}",
    }
    text = (V2/"chapter_11.md").read_text()
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    assert not re.search(r"\{\{[A-Z0-9_]+\}\}", text)
    bars = [("1天XGBoost", metric(t35, "xgboost", 1)["pr_auc_average_precision"]),
            ("3天XGBoost", metric(t35, "xgboost", 3)["pr_auc_average_precision"]),
            ("7天XGBoost", metric(t35, "xgboost")["pr_auc_average_precision"]),
            ("XGBoost+Hawkes", metric(t37, "xgboost_hawkes")["pr_auc_average_precision"]),
            ("Hawkes（无标签）", metric(t36, "hawkes")["pr_auc_average_precision"]),
            ("7天逻辑回归", metric(t35, "logistic_regression")["pr_auc_average_precision"]),
            ("7天历史频率", metric(t35, "historical_frequency")["pr_auc_average_precision"]),
            ("仅A–A训练·B–B测试", holdout_ap)]
    return text, values, bars, metric(t35, "xgboost")["positive_rate"]


def figure(bars, prevalence):
    d = Drawing(450, 30 + 26*len(bars) + 30)
    x0, w0, y0 = 128, 270, 34
    for i, (name, v) in enumerate(reversed(bars)):
        y = y0 + i*26; w = w0*v/0.8
        br.label(d, x0-8, y+5, name, 9, "end"); d.add(Rect(x0, y, w, 16, fillColor=br.WHITE, strokeColor=br.BLACK)); br.hatch(d, x0, y, w, 16, 6 + i % 3)
        br.label(d, x0+w+5, y+4, f"{v:.3f}", 9, "start")
    px = x0 + w0*prevalence/0.8
    d.add(Line(px, y0-4, px, y0 + 26*len(bars), strokeColor=br.BLACK, strokeDashArray=[3, 2]))
    for v in (0, .2, .4, .6, .8):
        x = x0 + w0*v/.8; d.add(Line(x, y0-8, x, y0-4, strokeColor=br.BLACK)); br.label(d, x, y0-20, f"{v:.1f}", 9)
    br.label(d, 260, y0 + 26*len(bars) + 12, "合并AP；虚线为随机排序（正例率0.197）；11个测试日", 9)
    return d


def compose(v1, ch):
    text = v1
    text = text.replace("审阅与编制日期：2026年10月13日", "审阅与编制日期：2026年10月13日（第一版）；2026年10月28日（第二版，补充第11章）", 1)
    text = text.replace("材料范围：T01-T34、Product Extension P01-P03及已完成文档维护。", "材料范围：T01-T34、补充研究T35-T40、Product Extension P01-P03及已完成文档维护。第二版在第一版基础上新增第11章，原第11章结论顺延为第12章，其余章节保持第一版原文，文中的文件路径指第一版（478a320）时的位置。", 1)
    old_abs = "本文认为该项目形成了从数据诊断到结果审计的完整实践"
    assert old_abs in text
    text = text.replace(old_abs, "第二版补充的滚动起点重评估把测试日扩展到11天，7天XGBoost合并AP为0.662，比1天高0.090；不用标签的Hawkes过程达到0.629，留出参与者后模型仍保持0.651。" + old_abs, 1)
    text = text.replace("第10章讨论与未来工作；第11章结论；", "第10章讨论与未来工作；第11章补充研究；第12章结论；", 1)
    text = text.replace("## 第11章 结论", ch + "\n## 第12章 结论", 1)
    final = "总体而言，项目的实践价值不仅在于训练出一个模型"
    assert final in text
    text = text.replace(final, "第二版新增的第11章在不改动冻结证据的前提下，把可评估的测试日从4天扩展到11天：7天XGBoost的合并AP为0.662，比1天高0.090，11天全部为正。不用标签的Hawkes过程达到0.629，把它作为特征加入XGBoost只再提高0.003，说明主要信号来自最近接触的时间结构。留出参与者后，模型在未见人群上的AP为0.651，代价在0.02以内。这些测试日此前都已暴露，所以上述结果仍是描述性证据。\n\n" + final, 1)
    old_105 = "现有实验主要是同一人群内部的时间预测，不包含完全未见参与者或跨组织迁移。"
    assert old_105 in text
    text = text.replace(old_105, "第一版实验主要是同一人群内部的时间预测；第11章的T38在同一人群内留出了未见参与者，但仍不包含跨组织迁移。", 1)
    refs_end = text.index("## 附录A")
    text = text[:refs_end].rstrip() + "\n\n" + "\n\n".join(REFERENCES) + "\n\n" + text[refs_end:]
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serif", default="/System/Library/Fonts/Supplemental/Songti.ttc")
    parser.add_argument("--sans", default="/System/Library/Fonts/STHeiti Medium.ttc")
    args = parser.parse_args()
    pdfmetrics.registerFont(TTFont("ReportSong", args.serif, subfontIndex=6))
    pdfmetrics.registerFont(TTFont("ReportHei", args.sans, subfontIndex=1))
    pdfmetrics.registerFontFamily("ReportSong", normal="ReportSong", bold="ReportHei", italic="ReportSong", boldItalic="ReportHei")
    v1_path = ROOT/"deliverables/Encounter_Lab_Full_Report.md"
    v1_before = v1_path.read_bytes()
    data = load(); ch, values, bars, prevalence = chapter(data)
    v1 = v1_before.decode()
    text, blocks = br.fill_tables(compose(v1, ch), br.aggregates())
    (V2/"figures").mkdir(exist_ok=True)
    import tempfile
    with tempfile.TemporaryDirectory() as scratch:
        # First-edition figures are regenerated only to check they are byte-identical; v2 links to them.
        br.FIGDIR = Path(scratch)
        figs = br.figures(br.aggregates())
        for svg_path in Path(scratch).glob("*.svg"):
            assert svg_path.read_bytes() == (ROOT/"deliverables/Encounter_Lab_Report_Figures"/svg_path.name).read_bytes(), svg_path.name
    figs["figure_11_1"] = figure(bars, prevalence)
    svg = renderSVG.drawToString(figs["figure_11_1"]).replace("font-family: ReportSong", "font-family: Songti SC, SimSun, serif").replace("font-family: ReportHei", "font-family: Heiti SC, SimHei, sans-serif")
    (V2/"figures/figure_11_1.svg").write_text(svg)
    text = text.replace("](Encounter_Lab_Report_Figures/", "](../Encounter_Lab_Report_Figures/")
    MD.write_text(text)
    for name in ("ReportSong", "ReportHei"):
        font = pdfmetrics.getFont(name)
        missing = {c for c in text if ord(c) > 127 and ord(c) not in font.face.charToGlyph}
        assert not missing, (name, sorted(missing))
    headings = br.make_pdf(text, figs, output=PDF, cover=COVER)
    assert v1_path.read_bytes() == v1_before, "v1 report must stay byte-identical"
    body = text[text.index("## 第1章"):text.index("## 参考文献")]
    body = re.sub(r"(?m)^!\[.*?\]\([^)]*\)\s*$", "", body)
    record = {"version": 2, "date": "2026-10-28", "v1_sha256": hashlib.sha256(v1_before).hexdigest(),
              "study_sha256": {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in STUDIES.items()},
              "chapter_values": {k: v for k, v in values.items() if not k.endswith("TABLE")},
              "report_sha256": hashlib.sha256(MD.read_bytes()).hexdigest(), "pdf_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
              "chapters": len(re.findall(r"^## 第\d+章", text, re.M)), "figures": len(figs),
              "tables": len(re.findall(r"^表 [0-9A-G]+-\d+ ", text, re.M)), "references": len(re.findall(r"^\[\d+\] ", text, re.M)),
              "body_chinese_characters": len(re.findall(r"[一-鿿]", body)), "heading_pages": headings,
              "render_review": "see local render QA"}
    (V2/"REPORT_V2_VERIFICATION.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in ("chapters", "figures", "tables", "references", "body_chinese_characters")}, ensure_ascii=False))
    print("pages", headings[-1]["page"] if headings else None)


if __name__ == "__main__":
    main()

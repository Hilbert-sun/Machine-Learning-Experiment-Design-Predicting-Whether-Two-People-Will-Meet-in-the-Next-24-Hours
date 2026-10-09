import streamlit as st
from pathlib import Path
import plotly.express as px
import yaml

from src.loader import source_kind, supported_files
from src.overview import overview_summary
from src.pipeline_cache import file_signatures
from src.preprocessing import cached_dataset
from src.ui import dataset_picker


@st.cache_data(show_spinner=False, max_entries=8)
def cached_overview(root, config, dataset, processed, signature):
    return overview_summary(root, config, dataset, processed)

st.title("Encounter Lab · 相遇实验室")
st.caption("Can We Predict When Two People Meet Again?")
dataset = dataset_picker()
root = Path(__file__).resolve().parents[1]
config = yaml.safe_load((root / "configs/default.yaml").read_text())
paths = config.get("paths", {})
raw = root / paths.get("raw_copenhagen" if dataset == "Copenhagen" else "raw_sociopatterns", f"data/raw/{dataset.lower()}")
available = {}
for source in supported_files(raw, dataset):
    if source_kind(source, dataset) in {"bluetooth", "proximity"}:
        processed = cached_dataset(source, dataset, root / paths.get("processed", "data/processed"))
        if processed:
            available[source.name] = processed
summary = None
if available:
    source = st.selectbox("主接触文件", list(available)) if len(available) > 1 else next(iter(available))
    processed = available[source]
    dependency_paths = [processed.directory / name for name in ("contacts.parquet", "coverage.parquet")]
    dependency_paths += list((root / paths.get("processed", "data/processed") / "labels").glob("labels-*.parquet"))
    dependency_paths += list((root / paths.get("processed", "data/processed") / "labels").glob("labels-*.json"))
    dependency_paths += list((root / paths.get("models", "models")).rglob("manifest.json"))
    # Feature-manifest versions also determine whether a label artifact is current.
    dependency_paths += list((root / paths.get("features", "data/features")).glob("features-*.json"))
    dependency_paths += list((root / paths.get("features", "data/features")).glob("features-*.parquet"))
    with st.spinner("汇总当前清洗数据…"):
        summary = cached_overview(str(root), config, dataset, processed, file_signatures(dependency_paths))
    st.success(f"当前数据：{dataset} · {source} · 已清洗。")
    policy = config.get("prediction", {})
    st.caption(f"配置标签策略：每天{policy.get('snapshot_hour', 8):02d}:00、最低扫描覆盖率{policy.get('min_scan_coverage', 0.5):.0%}；主要评估可用样本：{summary['eligible_samples']:,}。标签或可靠分母缺失时正例率保持未知。")
else:
    st.info("尚无当前数据集的已验证清洗缓存。请从数据管理开始；模型和实验结果将在实际运行后展示。")

metrics = (
    ("参与者", "有效匿名参与者数量"),
    ("接触记录", "经过验证和清洗的接触测量记录数"),
    ("有效配对", "清洗后的无向配对数量"),
    ("观测天数", "数据覆盖的研究天数"),
    ("正例占比", "可评估样本中未来24小时发生接触的比例"),
    ("已保存模型", "当前数据集的已保存模型版本数；不代表已经运行预测"),
)
values = ["—"] * 6
if summary:
    values = [f"{summary['participants']:,}", f"{summary['contact_records']:,}", f"{summary['valid_pairs']:,}",
              str(summary["observation_days"]), f"{summary['positive_rate']:.1%}" if summary["positive_rate"] is not None else "未知",
              str(summary["saved_models"]) if summary["saved_models"] else "未训练"]
for offset in (0, 3):
    for index, (column, (label, explanation)) in enumerate(zip(st.columns(3), metrics[offset : offset + 3]), start=offset):
        column.metric(label, values[index], help=explanation)

if summary:
    data = summary["exploration"]
    for title, figure in (
        ("每日接触记录", px.line(data.daily, x="study_day", y="contact_records", markers=True, labels={"study_day": "Study Day", "contact_records": "接触记录数"})),
        ("研究日内小时活跃度", px.bar(data.hourly, x="hour", y="contact_records", labels={"hour": "研究日内小时", "contact_records": "接触记录数"})),
    ):
        figure.update_layout(title=f"{dataset} · {title} · 当前清洗缓存全观察范围")
        st.plotly_chart(figure, width="stretch")
    if data.coverage_mean is not None:
        st.plotly_chart(px.line(data.coverage, x="study_day", y="mean_scan_coverage", markers=True,
                                title=f"{dataset} · 平均扫描记录覆盖率 · 全观察范围", labels={"study_day": "Study Day", "mean_scan_coverage": "覆盖率"}), width="stretch")
    else:
        st.info("当前扫描覆盖率未知；正接触记录不能用于推断无接触或在线率。")

st.subheader("开始研究")
for column, (path, label) in zip(
    st.columns(4),
    (
        ("pages/1_Data_Manager.py", "加载数据"),
        ("pages/2_Data_Explorer.py", "探索数据"),
        ("pages/4_Model_Training.py", "训练模型"),
        ("pages/5_Prediction_Lab.py", "打开 Prediction Lab"),
    ),
):
    with column:
        st.page_link(path, label=label)
st.caption("时间轴使用 Study Day；无观测不代表无接触。")

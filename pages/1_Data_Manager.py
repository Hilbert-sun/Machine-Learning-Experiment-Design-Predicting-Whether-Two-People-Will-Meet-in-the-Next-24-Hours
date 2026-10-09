import streamlit as st
from pathlib import Path

import yaml

from src.ui import dataset_picker, source_links
from src.downloader import (
    DownloadError, download_file, fetch_copenhagen_files, save_upload,
    scan_local_files, sociopatterns_file,
)
from src.loader import SchemaError, supported_files, validate_file
from src.preprocessing import cached_dataset, preprocess_contacts
from src.label_builder import build_labels
from src.feature_engineering import build_features


def signature(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


@st.cache_data(show_spinner=False)
def cached_validation(path, dataset_name, file_signature):
    # The signature invalidates reports when local files change; cache only summaries.
    return validate_file(path, dataset_name).to_dict()

st.title("数据管理 · Data Manager")
dataset = dataset_picker()
source_links()
root = Path(__file__).resolve().parents[1]
config = yaml.safe_load((root / "configs/default.yaml").read_text())
directory = root / config["paths"]["raw_copenhagen" if dataset == "Copenhagen" else "raw_sociopatterns"]
st.caption(f"本地目录：{directory}")

st.subheader("获取数据")
if dataset == "Copenhagen":
    if st.button("读取官方文件清单"):
        try:
            with st.spinner("读取 Figshare 元数据…"):
                st.session_state["copenhagen_files"] = fetch_copenhagen_files()
        except DownloadError as exc:
            st.error(str(exc))
    files = st.session_state.get("copenhagen_files", [])
else:
    files = [sociopatterns_file()]
    st.caption("SocioPatterns 未提供官方校验和；下载完成后还需验证文件结构。")

if files:
    by_name = {item.name: item for item in files}
    st.dataframe([
        {"文件": item.name, "字节": item.size, "MD5": item.md5 or "未提供"}
        for item in files
    ], hide_index=True, width="stretch")
    selected = st.multiselect("选择下载文件", list(by_name), default=list(by_name) if dataset == "SocioPatterns" else [])
    if st.button("下载所选文件", disabled=not selected):
        for name in selected:
            bar = st.progress(0.0, text=f"准备下载 {name}")

            def show_progress(done, total):
                bar.progress(min(done / total, 1.0) if total else 0.0, text=f"{name} · {done:,} / {total if total is not None else '未知'} 字节")

            try:
                result = download_file(by_name[name], directory, progress=show_progress)
                bar.progress(1.0, text=f"{name} 下载检查完成")
                st.success(f"{name}：{'本地已存在，跳过下载' if result.skipped else '下载成功'}。尚未完成数据字段验证。")
            except (DownloadError, OSError) as exc:
                st.error(str(exc))

with st.expander("手动上传 / 网络失败时恢复"):
    st.write("也可从上方官方链接下载文件并放入本地目录，然后扫描。上传不会覆盖已有文件。")
    uploads = st.file_uploader("上传原始文件", type=["csv", "gz", "readme", "ipynb"], accept_multiple_files=True)
    if st.button("保存上传文件", disabled=not uploads):
        for upload in uploads:
            try:
                upload.seek(0)
                save_upload(upload, upload.name, directory)
                st.success(f"已保存 {upload.name}，待验证。")
            except (ValueError, OSError) as exc:
                st.error(str(exc))

st.subheader("本地文件")
st.button("扫描本地文件 · Scan Local Files", help="页面每次刷新都会重新扫描；此按钮立即刷新文件列表。")
local_files = scan_local_files(directory)
if local_files:
    st.dataframe(local_files, hide_index=True, width="stretch")
else:
    st.info("Not Downloaded · 尚无本地文件。")

st.subheader("字段与文件验证")
sources = supported_files(directory, dataset)
st.caption("逐块检查完整文件。原始数据保留扫描标记、重复行与原始时间；清洗结果与观测覆盖率单独保存在下方预处理缓存。")
if st.button("验证本地数据", disabled=not sources):
    results = {}
    for path in sources:
        file_signature = signature(path)
        try:
            with st.spinner(f"Processing · 正在验证 {path.name}…"):
                report = cached_validation(str(path), dataset, file_signature)
            results[path.name] = {"signature": file_signature, "report": report}
        except SchemaError as exc:
            results[path.name] = {"signature": file_signature, "error": str(exc)}
    st.session_state[f"validation_{dataset}"] = results

results = st.session_state.get(f"validation_{dataset}", {})
current = {
    path.name: results[path.name] for path in sources
    if path.name in results and results[path.name]["signature"] == signature(path)
}
errors = [item["error"] for item in current.values() if "error" in item]
primary_kind = "bluetooth" if dataset == "Copenhagen" else "proximity"
ready = any(item.get("report", {}).get("kind") == primary_kind for item in current.values())
if errors:
    st.error("Validation Failed · 请检查以下错误，修复或重新下载文件后再验证。")
    for error in errors:
        st.error(error)
elif ready and len(current) == len(sources):
    st.success("Ready · 接触源文件结构验证通过，可运行预处理；训练仍需完成后续步骤。")
elif local_files:
    st.info("Downloaded · 请验证本地数据；主接触文件缺失时不能进入 Ready。")

for name, result in current.items():
    if "report" in result:
        report = result["report"]
        with st.expander(f"{name} · {report['rows']:,} 行 · 验证通过"):
            st.json({key: value for key, value in report.items() if key != "preview"})
            st.caption("预览：最多10行原始记录，字段别名已映射；尚未清洗。")
            st.dataframe(report["preview"], hide_index=True, width="stretch")
if dataset == "Copenhagen" and not any(path.name in {"bt_symmetric.csv", "bt.csv"} for path in sources):
    st.warning("缺少主接触文件 bt_symmetric.csv。仅有电话/短信文件不能用于接触预测。")
st.caption("README、Notebook、Facebook 与 gender 附属文件仅列出，不纳入当前接触/通信字段验证。无观测不代表无接触。")

st.subheader("数据预处理")
primary_sources = [path for path in sources if path.name in {
    "bt_symmetric.csv", "bt.csv", "HighSchool2013_proximity_net.csv.gz", "HighSchool2013_proximity_net.csv",
}]
primary = None
if len(primary_sources) == 1:
    primary = primary_sources[0]
elif primary_sources:
    name = st.selectbox("主接触文件（每次仅处理一个，避免重复计数）", [path.name for path in primary_sources])
    primary = next(path for path in primary_sources if path.name == name)
output = root / config["paths"]["processed"]
can_process = primary is not None and primary.name in current and "report" in current[primary.name] and not errors
st.caption("过滤无效/自身接触，统一无向配对，去除完全相同的接触记录；空扫描单独保留为观测证据。")
if st.button("运行预处理", disabled=not can_process):
    bar = st.progress(0.0, text="Processing · 准备清洗…")
    total = current[primary.name]["report"]["rows"]
    try:
        result = preprocess_contacts(
            primary, dataset, output,
            progress=lambda rows: bar.progress(min(rows / total, 1.0), text=f"Processing · 已读取 {rows:,} / {total:,} 行"),
        )
        bar.progress(1.0, text="预处理完成，缓存已保存" if not result.cached else "已复用匹配的预处理缓存")
    except (SchemaError, OSError, RuntimeError, ValueError) as exc:
        st.error(f"预处理失败：{exc}。请检查源文件与输出目录，修复后重新验证并重试。")

processed = cached_dataset(primary, dataset, output) if primary is not None else None
if processed:
    st.success(f"Processed · {processed.report['contact_rows']:,} 条有效接触，已保存本地缓存。尚未生成标签或训练模型。")
    st.caption(f"缓存目录：{processed.directory}")
    with st.expander("清洗与观测质量报告"):
        st.json(processed.report)
    if not processed.report["scan_coverage_available"]:
        st.info("SocioPatterns 仅记录正接触，扫描覆盖率未知；不能据此判定未见面。")
    else:
        st.caption("覆盖率 = 每位报告者的观测扫描窗口数 / 每完整研究日288个窗口，首末日也使用完整日分母。无扫描的窗口仍是未知观测，不是负例。")
else:
    st.info("尚无匹配的预处理缓存。请先验证主接触文件，再运行预处理。")

st.subheader("24小时标签与历史特征")
policy = config.get("prediction", {})
coverage_threshold = st.number_input("最低扫描覆盖率（实验策略）", min_value=0.01, max_value=1.0, value=float(policy.get("min_scan_coverage", 0.5)), step=0.05)
st.caption("默认每天08:00生成历史已知配对快照。低覆盖样本不进入主要评估；缺少可靠观测的无记录样本保持未知。")
label_key = f"labels_{processed.directory.name}_{coverage_threshold}_{policy.get('snapshot_hour', 8)}" if processed else None
labels = st.session_state.get(label_key) if label_key else None
if labels and not labels.path.is_file():
    labels = None
if st.button("生成24小时标签", disabled=processed is None):
    try:
        with st.spinner("生成历史候选配对与24小时标签…"):
            labels = build_labels(processed, output / "labels", snapshot_hour=policy.get("snapshot_hour", 8), min_scan_coverage=coverage_threshold)
        st.session_state[label_key] = labels
    except (OSError, ValueError, RuntimeError) as exc:
        st.error(f"标签生成失败：{exc}。请重新验证输入后重试。")
if labels:
    st.success(f"标签缓存：{labels.report['rows']:,} 个样本；正例 {labels.report['positive_labels']:,}，负例 {labels.report['negative_labels']:,}，未知 {labels.report['unknown_labels']:,}。")
    st.caption(f"主要评估可用：{labels.report['eligible_samples']:,} 个样本。标签窗口为 (t, t+24h]，不完整未来窗口已排除。")
    if labels.report["eligible_samples"] == 0:
        st.info("当前没有满足覆盖策略的主要评估样本。可检查历史特征，但不能据此训练或报告主要模型效果。")
    with st.expander("标签生成报告"):
        st.json(labels.report)

feature_policy = config.get("features", {})
feature_key = f"features_{labels.path.name}_{feature_policy.get('weekday_origin')}_{feature_policy.get('weekday_reference')}_{feature_policy.get('enable_communications', False)}" if labels else None
features = st.session_state.get(feature_key) if feature_key else None
if features and not features.path.is_file():
    features = None
if st.button("生成历史特征", disabled=labels is None or labels.report["rows"] == 0):
    try:
        with st.spinner("计算严格早于预测时刻的历史特征…"):
            features = build_features(processed, labels, root / config["paths"]["features"],
                                      weekday_origin=feature_policy.get("weekday_origin"), weekday_reference=feature_policy.get("weekday_reference"),
                                      communications_enabled=feature_policy.get("enable_communications", False))
        st.session_state[feature_key] = features
    except (OSError, ValueError, RuntimeError) as exc:
        st.error(f"特征生成失败：{exc}。请检查标签、配置与源文件后重试。")
if features:
    st.success(f"历史特征缓存：{features.report['rows']:,} 行；窗口为1/3/7/14天。尚未训练模型。")
    with st.expander("历史特征报告"):
        st.json(features.report)
st.caption("特征仅使用 [t-window, t)；网络也仅来自历史记录。通讯特征默认禁用，未确认的星期、扫描覆盖率和RSSI保持空值。")
st.page_link("pages/7_Data_Sources.py", label="查看数据来源与使用限制")

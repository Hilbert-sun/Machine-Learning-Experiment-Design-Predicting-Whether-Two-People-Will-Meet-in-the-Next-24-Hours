import streamlit as st
from pathlib import Path

import yaml

from src.ui import dataset_picker, source_links
from src.downloader import (
    DownloadError, download_file, fetch_copenhagen_files, save_upload,
    scan_local_files, sociopatterns_file,
)
from src.loader import SchemaError, supported_files, validate_file


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
st.caption("逐块检查完整文件。保留空扫描、外部设备、重复行与原始时间；清洗和覆盖率分析将在后续任务完成。")
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
    st.success("Ready · 接触源文件结构验证通过，尚未清洗、生成标签或训练模型。")
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
st.page_link("pages/7_Data_Sources.py", label="查看数据来源与使用限制")

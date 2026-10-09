from pathlib import Path

import streamlit as st
import yaml

from src.loader import source_kind, supported_files
from src.preprocessing import cached_dataset
from src.ui import dataset_picker
from src.visualization import exploration_figures, exploration_options, summarize_exploration


@st.cache_data(show_spinner=False, max_entries=8)
def cached_options(folder, report, file_signature):
    return exploration_options(folder, report)


@st.cache_data(show_spinner=False, max_entries=8)
def cached_summary(folder, report, file_signature, days, users, pair):
    return summarize_exploration(folder, report, days, users=users, pair=pair)


st.title("数据探索 · Data Explorer")
dataset = dataset_picker()
root = Path(__file__).resolve().parents[1]
config = yaml.safe_load((root / "configs/default.yaml").read_text())
raw = root / config["paths"]["raw_copenhagen" if dataset == "Copenhagen" else "raw_sociopatterns"]
output = root / config["paths"]["processed"]
available = {}
for path in supported_files(raw, dataset):
    if source_kind(path, dataset) in {"bluetooth", "proximity"}:
        processed = cached_dataset(path, dataset, output)
        if processed:
            available[path.name] = processed
if not available:
    st.info("尚无匹配当前源文件的清洗缓存。请先在 Data Manager 验证主接触文件并运行预处理。")
    st.page_link("pages/1_Data_Manager.py", label="前往数据管理")
    st.stop()

source = st.selectbox("主接触文件", list(available)) if len(available) > 1 else next(iter(available))
processed = available[source]
folder, report = processed.directory, processed.report
try:
    file_signature = tuple((name, (folder / name).stat().st_size, (folder / name).stat().st_mtime_ns) for name in ("contacts.parquet", "coverage.parquet"))
    options = cached_options(str(folder), report, file_signature)
    st.subheader("筛选范围")
    if options["first_day"] == options["last_day"]:
        days = (options["first_day"], options["last_day"])
        st.caption(f"Study Day {days[0]:02d}（缓存仅包含这一日）")
    else:
        days = st.slider("Study Day 范围", options["first_day"], options["last_day"], (options["first_day"], options["last_day"]), key=f"days_{folder.name}")
    users = st.multiselect("匿名参与者 ID（任一端命中）", options["users"], key=f"users_{folder.name}")
    pair = None
    if st.checkbox("限定一个无向配对", disabled=len(options["users"]) < 2, key=f"pair_enabled_{folder.name}"):
        a = st.selectbox("配对参与者 A", options["users"], key=f"pair_a_{folder.name}")
        b = st.selectbox("配对参与者 B", [user for user in options["users"] if user != a], key=f"pair_b_{folder.name}")
        pair = (a, b)
    scope = f"{dataset} · Study Day {days[0]:02d}–{days[1]:02d}"
    def user_label(ids):
        return ", ".join(map(str, ids)) if len(ids) <= 5 else f"{len(ids)}名所选参与者"
    contact_scope = scope + " · " + ("用户 " + user_label(users) if users else "全部用户")
    if pair:
        contact_scope += f" · 配对 {min(pair)}–{max(pair)}"
    coverage_scope = scope + " · 覆盖率用户 " + (user_label(users or pair) if users or pair else "全部参与者")
    st.caption(f"来源文件：{source}")
    st.caption(contact_scope)
    st.caption("用户筛选与配对筛选取交集。每个接触记录是清洗后的独立测量，不等同于一次连续见面；频率分布仅包含有记录的配对。0计数只表示没有记录，不代表确定没有接触。")
    with st.spinner("按筛选范围汇总清洗记录…"):
        data = cached_summary(str(folder), report, file_signature, days, tuple(users), pair)
    cols = st.columns(4)
    cols[0].metric("接触记录", f"{data.rows:,}")
    cols[1].metric("有记录的配对", f"{len(data.pairs):,}")
    cols[2].metric("有接触的参与者", f"{len(data.activity):,}")
    cols[3].metric("平均扫描记录覆盖率", f"{data.coverage_mean:.1%}" if data.coverage_mean is not None else "未知", help=coverage_scope)
    if data.rows == 0:
        st.info("当前筛选下没有接触记录。仍显示对应参与者的观测状态；0条记录不能证明没有接触。")
    if data.rssi.empty or not data.rssi.records.sum():
        st.info("当前范围没有可用的 RSSI 测量，不生成虚构分布。")
    if data.coverage_mean is None:
        st.info("扫描覆盖率未知：正接触记录不能代替扫描日志，不能用其缺失判断没有见面。")
    st.caption("覆盖率按所选用户计算；未选用户时按配对两端，否则按全部参与者。配对过滤不会删除扫描证据。")
    st.caption("Copenhagen 覆盖率以每完整研究日288个5分钟窗口为分母，首末不足一日仍用相同分母；无扫描表示未知观测。小时按缓存时间原点计算，SocioPatterns 为 UNIX 整日锚点，不代表当地钟表时间。")
    figures = exploration_figures(data, contact_scope)
    for index, (title, figure) in enumerate(figures.items()):
        if title in {"扫描记录覆盖率", "扫描与缺失观测状态"}:
            figure.update_layout(title={"text": f"{title}<br><sup>{coverage_scope}</sup>"})
        if index % 2 == 0:
            columns = st.columns(2)
        with columns[index % 2]:
            st.plotly_chart(figure, width="stretch", key=f"chart_{index}")
    st.caption("排名和热力图最多显示筛选后最活跃的20人；热力图为对称接触记录计数。所有统计为回顾性探索，不作为预测结果或未来特征。")
except (OSError, ValueError, KeyError) as exc:
    st.error(f"无法读取清洗缓存：{exc}。请返回 Data Manager 重新验证并预处理。")
    st.page_link("pages/1_Data_Manager.py", label="前往数据管理")

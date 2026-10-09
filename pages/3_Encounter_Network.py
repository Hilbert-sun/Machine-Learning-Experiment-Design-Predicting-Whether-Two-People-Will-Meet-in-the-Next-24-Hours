from pathlib import Path

import streamlit as st
import yaml

from src.loader import source_kind, supported_files
from src.network import bounded_network, historical_network, network_figure, selected_node
from src.pipeline_cache import file_signatures
from src.preprocessing import cached_dataset
from src.ui import dataset_picker


@st.cache_data(show_spinner=False, max_entries=8)
def cached_graph(processed, signatures, timestamp, window):
    return historical_network(processed, timestamp, window)


st.title("相遇网络 · Encounter Network")
dataset = dataset_picker()
root = Path(__file__).resolve().parents[1]
config = yaml.safe_load((root / "configs/default.yaml").read_text())
raw = root / config["paths"]["raw_copenhagen" if dataset == "Copenhagen" else "raw_sociopatterns"]
available = {}
for path in supported_files(raw, dataset):
    if source_kind(path, dataset) in {"bluetooth", "proximity"}:
        processed = cached_dataset(path, dataset, root / config["paths"]["processed"])
        if processed:
            available[path.name] = processed
if not available:
    st.info("尚无匹配的清洗缓存。请先在 Data Manager 验证主接触文件并运行预处理。")
    st.page_link("pages/1_Data_Manager.py", label="前往数据管理")
    st.stop()
source = st.selectbox("主接触文件", list(available)) if len(available) > 1 else next(iter(available))
processed = available[source]
last = processed.report["source_timestamp_max"] - processed.report["time_origin_seconds"]
day = int(st.number_input("预测时点 · Study Day", min_value=1, max_value=last // 86400 + 2, value=last // 86400 + 2))
hour = int(st.number_input("预测小时", min_value=0, max_value=23, value=0))
window = st.selectbox("历史窗口（天）", [1, 3, 7, 14], index=2)
nodes = st.slider("最多显示节点数", 2, 100, 30)
edges = st.slider("最多显示边数", 1, 300, 100)
search = st.text_input("查找匿名ID")
focus = None
if search:
    try:
        focus = int(search)
        if focus < 0:
            raise ValueError
    except ValueError:
        st.error("请输入非负整数匿名ID。")
        st.stop()
t = (day - 1) * 86400 + hour * 3600
try:
    with st.spinner("构建预测时刻之前的历史网络…"):
        graph = cached_graph(processed, file_signatures([processed.directory / "contacts.parquet"]), t, window)
    st.caption(f"{dataset} · {source} · Study Day {day:02d} {hour:02d}:00之前{window}天 · 区间 [t-window,t)")
    if not graph:
        st.info("所选历史窗口没有有效接触记录；这不能证明没有接触。")
        st.stop()
    if focus is not None and focus not in graph:
        st.info("此匿名ID在所选历史窗口没有有效接触记录。")
    rendered = bounded_network(graph, max_nodes=nodes, max_edges=edges, focus=focus)
    st.caption(f"完整历史窗口：{len(graph):,}人、{graph.number_of_edges():,}个有记录的配对；当前显示{len(rendered)}节点、{rendered.number_of_edges()}边。节点大小/边宽分别对应历史活跃度/接触记录数。")
    graph_key = f"network_{processed.directory.name}_{t}_{window}_{nodes}_{edges}_{focus}"
    event = st.plotly_chart(network_figure(rendered, f"历史网络 · Study Day {day:02d} {hour:02d}:00 · {window}天窗口", focus=focus), width="stretch", key=graph_key, on_select="rerun", selection_mode="points")
    clicked = selected_node(event)
    user = clicked if clicked in graph else focus if focus in graph else st.selectbox("查看匿名节点历史统计", sorted(graph))
    st.subheader(f"匿名ID {user} · 完整所选历史窗口")
    st.json({"接触记录": graph.nodes[user]["activity"], "历史邻居": graph.nodes[user]["historical_degree"], "最近接触时间（相对秒）": graph.nodes[user]["last_contact"]})
    neighbors = sorted(graph[user].items(), key=lambda item: (-item[1]["weight"], item[0]))[:20]
    st.dataframe([{"邻居ID": neighbor, "接触记录": details["weight"], "最近接触时间": details["last_contact"]} for neighbor, details in neighbors], hide_index=True)
    st.caption("可点击节点查看历史统计。绘图限制不会改变完整历史统计；接触记录不等同于真实交谈或社交关系。")
except (OSError, ValueError, KeyError) as exc:
    st.error(f"无法构建网络：{exc}。请重新验证并预处理数据。")

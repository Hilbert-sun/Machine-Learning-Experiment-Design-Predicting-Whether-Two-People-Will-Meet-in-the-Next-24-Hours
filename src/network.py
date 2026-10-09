"""Historical-only contact networks, bounded rendering and Plotly node selection."""

from collections import Counter
import math

import networkx as nx
import plotly.graph_objects as go
import pyarrow.dataset as ds

from src.pipeline_cache import parquet_frames

DAY = 86400


def historical_network(processed, timestamp, window_days=7):
    if timestamp < 0 or window_days not in (1, 3, 7, 14):
        raise ValueError("预测时刻或历史窗口无效。")
    weights, last_seen = Counter(), {}
    expression = (ds.field("timestamp") >= timestamp - window_days * DAY) & (ds.field("timestamp") < timestamp)
    for frame in parquet_frames(processed.directory / "contacts.parquet", ["timestamp", "user_min", "user_max"], expression):
        weights.update(frame.groupby(["user_min", "user_max"]).size().to_dict())
        for pair, time in frame.groupby(["user_min", "user_max"]).timestamp.max().items():
            last_seen[pair] = max(last_seen.get(pair, -1), int(time))
    graph = nx.Graph(timestamp=int(timestamp), window_days=window_days)
    for (a, b), weight in sorted(weights.items()):
        graph.add_edge(int(a), int(b), weight=int(weight), last_contact=last_seen[(a, b)])
    for user in graph:
        graph.nodes[user]["activity"] = sum(edge["weight"] for edge in graph[user].values())
        graph.nodes[user]["historical_degree"] = graph.degree(user)
        graph.nodes[user]["last_contact"] = max(edge["last_contact"] for edge in graph[user].values())
    return graph


def bounded_network(graph, *, max_nodes=30, max_edges=100, focus=None):
    if not 2 <= max_nodes <= 100 or not 1 <= max_edges <= 300:
        raise ValueError("渲染范围最多100节点/300边，至少2节点/1边。")
    nodes = sorted(graph, key=lambda user: (-graph.nodes[user]["activity"], user))[:max_nodes]
    required = []
    if focus in graph:
        required = [focus, max(graph[focus], key=lambda user: (graph[focus][user]["weight"], -user))]
    for user in required:
        if user not in nodes:
            replace = next(index for index in range(len(nodes) - 1, -1, -1) if nodes[index] not in required)
            nodes[replace] = user
    subgraph = graph.subgraph(nodes)
    edges = sorted(subgraph.edges(data=True), key=lambda edge: (-edge[2]["weight"], min(edge[:2]), max(edge[:2])))[:max_edges]
    if focus in subgraph and not any(focus in (a, b) for a, b, _ in edges):
        edge = max(subgraph.edges(focus, data=True), key=lambda item: item[2]["weight"], default=None)
        if edge:
            edges[-1:] = [edge]
    rendered = nx.Graph(**graph.graph)
    rendered.add_nodes_from((user, dict(graph.nodes[user])) for user in sorted(nodes))
    rendered.add_edges_from(edges)
    return rendered


def network_figure(graph, scope, *, focus=None):
    positions = nx.spring_layout(graph, seed=42, weight="weight") if len(graph) else {}
    figure = go.Figure()
    maximum = max((edge["weight"] for _, _, edge in graph.edges(data=True)), default=1)
    for a, b, edge in graph.edges(data=True):
        figure.add_scatter(x=[positions[a][0], positions[b][0]], y=[positions[a][1], positions[b][1]], mode="lines",
                           line={"width": 1 + 4 * math.log1p(edge["weight"]) / math.log1p(maximum), "color": "#6D8495"},
                           text=f"{a}–{b} · {edge['weight']}条接触记录", hoverinfo="text", showlegend=False)
    users = list(graph)
    maximum_activity = max((graph.nodes[user]["activity"] for user in users), default=1)
    figure.add_scatter(x=[positions[user][0] for user in users], y=[positions[user][1] for user in users], mode="markers+text",
                       text=[str(user) for user in users], textposition="top center", ids=[str(user) for user in users],
                       customdata=[[user, graph.nodes[user]["activity"], graph.nodes[user]["historical_degree"]] for user in users],
                       marker={"size": [10 + 22 * math.sqrt(graph.nodes[user]["activity"] / maximum_activity) for user in users],
                               "color": ["#E4AE63" if user == focus else "#63C7B2" for user in users]},
                       hovertemplate="匿名ID %{customdata[0]}<br>历史接触记录 %{customdata[1]}<br>历史邻居 %{customdata[2]}<extra></extra>", showlegend=False)
    figure.update_layout(title=scope, height=550, xaxis={"visible": False}, yaxis={"visible": False}, clickmode="event+select", margin={"l": 10, "r": 10, "t": 65, "b": 10})
    return figure


def selected_node(event):
    for point in event.get("selection", {}).get("points", []):
        data = point.get("customdata")
        if isinstance(data, (list, tuple)) and data:
            try:
                return int(data[0])
            except (TypeError, ValueError):
                continue
    return None

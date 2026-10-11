"""Small self-report clue diagrams, never research-ID or social-network inference."""
import html

import networkx as nx
import plotly.graph_objects as go

MUTUAL_OPTIONS={'none':'没有','one':'大约1人','two':'大约2人','three_five':'大约3–5人','more':'更多','unknown':'不确定'}
COLORS={'frequency':'#63C7B2','distance':'#89A9E8','area':'#A994E6','timing':'#E4AE63','recency':'#DB8BA7','summary':'#B4C4D1'}


def clue_graph(result,mutual=None):
    if mutual is not None and mutual not in MUTUAL_OPTIONS:raise ValueError('共同熟人选项无效。')
    graph=nx.Graph(provenance='questionnaire_clues',meaning='问卷关联示意，不是真实社交关系网络')
    if result.status!='ready':return graph
    graph.add_nodes_from([('A',{'label':'A','kind':'person','description':'问卷中的 A，并非研究参与者 ID。','points':100}),
                          ('B',{'label':'B','kind':'person','description':'问卷中的 B，并非研究参与者 ID。','points':100})])
    for card in result.keywords:
        node='clue:'+card.field
        graph.add_node(node,label=card.name,kind=card.field,description=card.source+'；'+card.direction+'。'+card.explanation,points=card.points)
        for person in ('A','B'):graph.add_edge(person,node,weight=.3+card.points/100)
    if mutual not in (None,'none','unknown'):
        graph.add_node('summary:mutual',label='共同熟人（自述'+MUTUAL_OPTIONS[mutual]+'）',kind='summary',
                       description='仅为用户自述的汇总范围，不代表已知的具体朋友或新增评分因素。')
        for person in ('A','B'):graph.add_edge(person,'summary:mutual',weight=.6)
    if len(graph)>15:raise ValueError('线索图最多15个节点。')
    return graph


def graph_positions(graph):
    ordered=nx.Graph()
    ordered.add_nodes_from(sorted(graph.nodes(data=True)))
    ordered.add_edges_from(sorted(graph.edges(data=True)))
    if not graph:return {}
    positions=nx.spring_layout(ordered,seed=42,iterations=80,weight='weight')
    return {n:(float(p[0]),float(p[1])) for n,p in positions.items()}


def clue_figure(graph,focus='all'):
    if len(graph)>15 or graph.number_of_edges()>30:raise ValueError('图谱超过安全显示范围。')
    if graph.graph.get('provenance')!='questionnaire_clues':raise ValueError('不能把科研网络混入个人线索图。')
    positions=graph_positions(graph);figure=go.Figure()
    for a,b,edge in sorted(graph.edges(data=True)):
        figure.add_scatter(x=[positions[a][0],positions[b][0]],y=[positions[a][1],positions[b][1]],mode='lines',
            line={'color':'rgba(145,163,188,0.30)','width':1+edge.get('weight',.3)},hoverinfo='skip',showlegend=False)
    nodes=sorted(graph)
    active=set(graph) if focus=='all' or focus not in graph else {focus,*graph.neighbors(focus)}
    figure.add_scatter(x=[positions[n][0] for n in nodes],y=[positions[n][1] for n in nodes],mode='markers+text',
        text=[graph.nodes[n]['label'] for n in nodes],textposition='top center',ids=nodes,customdata=[[n] for n in nodes],
        hovertext=[html.escape(graph.nodes[n]['description']) for n in nodes],hovertemplate='%{hovertext}<extra></extra>',
        marker={'size':[28 if graph.nodes[n]['kind']=='person' else 22 if graph.nodes[n]['kind']=='summary' else 15+graph.nodes[n]['points']/10 for n in nodes],
                'color':['#EEF3FA' if graph.nodes[n]['kind']=='person' else COLORS.get(graph.nodes[n]['kind'],'#B4C4D1') for n in nodes],
                'opacity':[1 if n in active else .25 for n in nodes],'line':{'width':2,'color':'#273344'}},showlegend=False)
    figure.update_layout(title='A 和 B 的线索如何关联？',paper_bgcolor='#10141C',plot_bgcolor='#10141C',font={'color':'#E4E9F2'},
        xaxis={'visible':False},yaxis={'visible':False,'scaleanchor':'x'},height=440,margin={'l':45,'r':45,'t':65,'b':35},
        clickmode='event+select',uirevision='questionnaire-clues-v1')
    return figure


def clicked_clue(event,graph):
    for point in event.get('selection',{}).get('points',[]):
        value=point.get('customdata')
        if isinstance(value,(list,tuple)) and value and isinstance(value[0],str) and value[0] in graph:return value[0]
    return None

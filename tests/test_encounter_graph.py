"""Synthetic A/B diagrams: deterministic, bounded and no invented acquaintances."""
from dataclasses import replace

import networkx as nx
import pytest

from src.chance_encounter import evaluate_questionnaire
from src.encounter_graph import clue_graph,clue_figure,graph_positions,clicked_clue
from test_encounter_insights import ANSWERS


def test_only_known_keywords_are_graph_nodes_and_no_friend_inference():
    result=evaluate_questionnaire(replace(ANSWERS,distance='unknown',timing='unknown'))
    graph=clue_graph(result)
    assert set(graph)=={'A','B',*(('clue:'+c.field) for c in result.keywords)}
    assert not graph.has_edge('A','B')
    assert [n for n,d in graph.nodes(data=True) if d['kind']=='person']==['A','B']
    assert graph.graph['provenance']=='questionnaire_clues'


@pytest.mark.parametrize('mutual',[None,'none','unknown'])
def test_unprovided_acquaintances_create_no_summary(mutual):
    graph=clue_graph(evaluate_questionnaire(ANSWERS),mutual)
    assert 'summary:mutual' not in graph and len(graph)==7


@pytest.mark.parametrize('mutual,label',[('one','大约1人'),('two','大约2人'),('three_five','大约3–5人'),('more','更多')])
def test_acquaintance_range_is_one_summary_never_individual_people(mutual,label):
    result=evaluate_questionnaire(ANSWERS);graph=clue_graph(result,mutual)
    assert len(graph)==8 and graph.number_of_edges()==12
    assert label in graph.nodes['summary:mutual']['label']
    assert 'points' not in graph.nodes['summary:mutual']
    figure=clue_figure(graph)
    assert figure.data[-1].marker.size[list(figure.data[-1].ids).index('summary:mutual')]==22
    assert len([n for n,d in graph.nodes(data=True) if d['kind']=='person'])==2
    assert result.score==66


def test_layout_and_focus_are_repeatable_and_restore_identical_positions():
    graph=clue_graph(evaluate_questionnaire(ANSWERS))
    assert graph_positions(graph)==graph_positions(graph)
    reordered=nx.Graph(**graph.graph)
    reordered.add_nodes_from(reversed(list(graph.nodes(data=True))))
    reordered.add_edges_from(reversed(list(graph.edges(data=True))))
    assert graph_positions(graph)==graph_positions(reordered)
    all_view=clue_figure(graph);focused=clue_figure(graph,'A');restored=clue_figure(graph)
    assert list(all_view.data[-1].x)==list(focused.data[-1].x)==list(restored.data[-1].x)
    b=list(focused.data[-1].ids).index('B')
    assert focused.data[-1].marker.opacity[b]==.25


def test_empty_single_node_edgeless_and_limits():
    empty=clue_graph(evaluate_questionnaire(ANSWERS.__class__()))
    assert not empty and graph_positions(empty)=={}
    assert len(clue_figure(empty).data[-1].x)==0
    single=nx.Graph(provenance='questionnaire_clues')
    single.add_node('A',label='A',kind='person',description='fixture',points=100)
    assert len(clue_figure(single).data[-1].x)==1
    single.add_node('B',label='B',kind='person',description='fixture',points=100)
    assert len(clue_figure(single).data[-1].x)==2
    oversized=nx.Graph(provenance='questionnaire_clues');oversized.add_nodes_from(range(16))
    with pytest.raises(ValueError,match='安全显示范围'):clue_figure(oversized)
    with pytest.raises(ValueError):clue_graph(evaluate_questionnaire(ANSWERS),'unrecognized')


def test_research_graph_cannot_enter_personal_renderer_and_clicks_are_validated():
    research=nx.Graph();research.add_edge(101,202,weight=1)
    with pytest.raises(ValueError,match='科研网络'):clue_figure(research)
    graph=clue_graph(evaluate_questionnaire(ANSWERS))
    assert clicked_clue({'selection':{'points':[{'customdata':['A']}]}},graph)=='A'
    for data in (None,[],[101],[[]],['research:101']):
        assert clicked_clue({'selection':{'points':[{'customdata':data}]}},graph) is None

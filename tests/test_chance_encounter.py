"""Synthetic questionnaire cases only; no real people, datasets or model training."""
from dataclasses import replace
import itertools

import pytest

from src.chance_encounter import OPTIONS, POINTS, Questionnaire, evaluate_questionnaire

BASE=Questionnaire('friend','walkable','three_five','week','sometimes','sometimes','no')


def test_deterministic_published_formula_and_cards():
    result=evaluate_questionnaire(BASE)
    assert result==evaluate_questionnaire(BASE)
    assert result.score==66 and result.level=='中等'
    assert result.status=='ready' and len(result.keywords)==5
    assert result.rule_version=='p01_equal_mean_v1'
    assert sum(c.points for c in result.keywords)==330
    assert all(c.source=='用户填写：'+OPTIONS[c.field][getattr(BASE,c.field)] for c in result.keywords)


@pytest.mark.parametrize('relation',OPTIONS['relationship'])
def test_relationship_has_no_score_weight(relation):
    assert evaluate_questionnaire(replace(BASE,relationship=relation)).score==66


@pytest.mark.parametrize('field',POINTS)
def test_monotonic_factor_points_and_score(field):
    # Ignore the other historical category to avoid introducing contradictions.
    other='recency' if field=='frequency' else 'frequency'
    start=replace(BASE,**{other:'unknown'})
    results=[evaluate_questionnaire(replace(start,**{field:key})) for key,points in sorted(POINTS[field].items(),key=lambda p:p[1])]
    assert all(r.status=='ready' for r in results)
    assert [r.score for r in results]==sorted(r.score for r in results)


def test_unknown_and_missing_are_omitted_not_zero_or_evidence():
    unknown=evaluate_questionnaire(replace(BASE,distance='unknown',recency='unknown'))
    missing=evaluate_questionnaire(replace(BASE,distance=None,recency=None))
    assert unknown==missing and unknown.score==60
    assert len(unknown.keywords)==3
    assert set(unknown.unknown_fields)=={'distance','recency'}
    assert not any(c.field in unknown.unknown_fields for c in unknown.keywords)


@pytest.mark.parametrize('known_count',[0,1,2])
def test_insufficient_support_has_no_index_or_keyword_claims(known_count):
    fields=list(POINTS)
    values={field:getattr(BASE,field) if i<known_count else 'unknown' for i,field in enumerate(fields)}
    result=evaluate_questionnaire(replace(BASE,**values))
    assert result.status=='insufficient' and result.score is None and not result.keywords


@pytest.mark.parametrize('frequency,recency',[
    ('one_two','older'),('three_five','never'),('six_plus','older'),
    ('zero','day'),('zero','week'),('zero','month'),
])
def test_obvious_history_conflicts_rejected(frequency,recency):
    result=evaluate_questionnaire(replace(BASE,frequency=frequency,recency=recency))
    assert result.status=='inconsistent' and result.score is None and not result.keywords


@pytest.mark.parametrize('arrangement,status',[('yes','out_of_scope'),('unknown','needs_confirmation'),(None,'needs_confirmation')])
def test_arrangement_gate_even_without_other_answers(arrangement,status):
    result=evaluate_questionnaire(Questionnaire(arrangement=arrangement))
    assert result.status==status and result.score is None


@pytest.mark.parametrize('field',OPTIONS)
def test_unrecognized_or_wrong_type_input_rejected_without_echo(field):
    for value in ('untrusted-input',42,False,['friend']):
        result=evaluate_questionnaire(replace(BASE,**{field:value}))
        assert result.status=='invalid' and result.score is None
        assert 'untrusted-input' not in result.message


def test_schema_and_missing_relationship():
    with pytest.raises(ValueError): Questionnaire.from_mapping({'unexpected_field':'value'})
    with pytest.raises(ValueError): Questionnaire.from_mapping(None)
    with pytest.raises(TypeError): evaluate_questionnaire({})
    assert Questionnaire.from_mapping(BASE.__dict__)==BASE
    assert evaluate_questionnaire(replace(BASE,relationship=None)).status=='invalid'


def test_all_coarse_combinations_bounds_and_eligibility():
    # Exhaustive five-factor grid is small, pure and deterministic (~2k cases).
    for combination in itertools.product(*(tuple(v)+('unknown',) for v in POINTS.values())):
        result=evaluate_questionnaire(replace(BASE,**dict(zip(POINTS,combination))))
        if result.status=='ready':
            assert 0<=result.score<=100 and 3<=len(result.keywords)<=5
        else:
            assert result.score is None
    assert evaluate_questionnaire(replace(BASE,distance='same_area',frequency='six_plus',recency='day',area='often',timing='often')).score==100
    assert evaluate_questionnaire(replace(BASE,distance='different_city',frequency='zero',recency='never',area='rare',timing='different')).score==0

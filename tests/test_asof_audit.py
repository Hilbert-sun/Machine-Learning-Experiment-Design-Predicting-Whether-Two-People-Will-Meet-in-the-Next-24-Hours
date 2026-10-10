"""T30 offline batches reproduce T28 and keep unknown labels out of metrics."""

import json

import numpy as np
import pandas as pd
import pytest

from src.asof_audit import load_audit_models,predict_snapshot,reveal_snapshot,attach_old_cohort,summarize
from src.asof_inference import InferenceError,predict_as_of,reveal_outcome
from src.window_cohort import KEYS,DAY
from test_time_machine import processed,models,model_rows
from test_asof_inference import T,append_contacts,modify_contacts,modify_observations


@pytest.fixture
def audit_models(model_rows):return load_audit_models(list(model_rows.values()))


def make_population(processed):
    append_contacts(processed,[(T-200,1,9),(T-100,1,3),(T-50,1,4)])
    modify_observations(processed,lambda f:f.loc[~(f.user_id.eq(3)&f.timestamp.gt(T))])


def test_batch_predictions_match_individual_T28_and_future_rows_cannot_change_them(processed,audit_models,monkeypatch):
    make_population(processed)
    before=predict_snapshot(processed,T,audit_models)
    assert len(before)==5 and before.prediction_available.sum()==4
    for model in audit_models:
        for row in before.loc[before.prediction_available].itertuples():
            actual=predict_as_of(processed,model.directory,T,row.user_min,row.user_max,dataset_id='copenhagen',history_window_days=model.window,evidence_path=model.evidence)
            np.testing.assert_allclose(actual['probability'],getattr(row,f'p_{model.tag}'),rtol=1e-12,atol=1e-12)
    append_contacts(processed,[(T,1,9),(T+1,1,3),(T+DAY,1,4)])
    modify_observations(processed,lambda f:f.assign(scan_observed=f.scan_observed.where(f.timestamp.lt(T),False)))
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('Prediction opened an evaluation bank/target table.'))
    pd.testing.assert_frame_equal(before,predict_snapshot(processed,T,audit_models))


def test_outcome_batch_matches_T28_positive_unknown_and_covered_absence(processed,audit_models):
    make_population(processed);pred=predict_snapshot(processed,T,audit_models)
    labels=reveal_snapshot(processed,T,pred,min_scan_coverage=0.5,backtest=True)
    assert labels.label_24h.eq(1).sum()==2 and labels.label_24h.eq(0).sum()==1 and labels.label_24h.isna().sum()==2
    for row in labels.itertuples():
        actual=reveal_outcome(processed,T,row.user_min,row.user_max,backtest=True,min_scan_coverage=0.5)
        assert actual['outcome']==row.outcome and actual['reason']==row.outcome_reason
    #Positive2-3 remains known even though device3 future coverage is zero.
    assert not labels.loc[labels.user_min.eq(2),'strict_future_covered'].iloc[0]


def test_reveal_requires_authorization_before_any_future_read(processed,audit_models,monkeypatch):
    pred=predict_snapshot(processed,T,audit_models)
    import src.asof_audit as module
    monkeypatch.setattr(module,'parquet_frames',lambda *a,**k:pytest.fail('Unauthorised future read.'))
    with pytest.raises(InferenceError,match='explicit_backtest'):reveal_snapshot(processed,T,pred,min_scan_coverage=0.5)


def samples_with_old(processed,audit_models):
    make_population(processed);pred=predict_snapshot(processed,T,audit_models)
    labels=reveal_snapshot(processed,T,pred,min_scan_coverage=0.5,backtest=True)
    samples=pred.merge(labels,on=KEYS,validate='one_to_one')
    old=labels.loc[labels.strict_future_covered,KEYS+['label_24h']]
    return attach_old_cohort(samples,old)


def test_unknowns_excluded_common_population_metrics_and_error_counts_recompute(processed,audit_models):
    samples=samples_with_old(processed,audit_models);specs=[m.spec() for m in audit_models]
    summary=summarize(samples,specs)
    assert summary['candidates']==5 and summary['prediction_available']==4
    assert summary['reliable_labels']==3 and summary['unknown_labels']==2
    rows=[r for r in summary['metrics'] if r['scope']=='reliable_predicted']
    assert len(rows)==3 and {r['rows'] for r in rows}=={3}
    assert all(r['positive_rate']==pytest.approx(2/3) for r in rows)
    modified=samples.copy()
    for spec in specs:modified.loc[~modified.reliable_label,f"p_{spec['tag']}"]=0.999
    assert summarize(modified,specs)['metrics']==summary['metrics']
    for row in summary['errors']:assert sum(row[k] for k in ('true_positive','false_positive','true_negative','false_negative'))==3
    assert all(r['confidence_interval'] is None for r in summary['paired_descriptive_contrasts'])
    assert summary['population_distributions'][-1]['positive_rate_reliable_only']==1


def test_empty_reliable_subset_has_no_invented_metrics(processed,audit_models):
    samples=samples_with_old(processed,audit_models)
    samples['label_24h']=pd.Series(pd.NA,index=samples.index,dtype='Int8');samples['reliable_label']=False
    samples['strict_future_covered']=False;samples['in_old_t22']=False
    summary=summarize(samples,[m.spec() for m in audit_models])
    assert all(r['rows']==0 and r['pr_auc_average_precision'] is None and r['roc_auc'] is None for r in summary['metrics'])


def test_model_deadline_mixed_coverage_and_old_label_mismatch_refuse(processed,model_rows,audit_models):
    with pytest.raises(InferenceError,match='information_conflict'):predict_snapshot(processed,6*DAY,audit_models)
    path=model_rows[3]['evidence_path'];record=json.loads(open(path).read());record['protocol']['coverage_threshold']=0.75
    #Use native contract on one window to create a genuinely mixed fixture, not a free descriptor value.
    manifest_path=audit_models[0].directory/'manifest.json';manifest=json.loads(manifest_path.read_text())
    manifest['metadata']['as_of_inference']={'schema_version':1,'feature_contract':'bounded_window_v1','feature_version':1,'dataset_id':'copenhagen',
        'history_window_days':audit_models[0].window,'prediction_horizon_hours':24,'min_scan_coverage':0.25,'time_origin_seconds':0,
        'label_information_ends':audit_models[0].contract.label_information_ends}
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(InferenceError,match='coverage policy'):load_audit_models(list(model_rows.values()))
    samples=samples_with_old(processed,audit_models)
    bad=samples.loc[samples.in_old_t22,KEYS+['label_24h']].copy();bad['label_24h']=1-bad.label_24h
    with pytest.raises(InferenceError,match='labels disagree'):attach_old_cohort(samples.drop(columns='in_old_t22'),bad)


def test_window_key_order_mismatch_is_rejected_before_position_based_scoring(processed,audit_models,monkeypatch):
    import src.asof_audit as module
    actual=module.as_of_features
    def reversed_bank(*args,**kwargs):
        banks=actual(*args,**kwargs);banks[3]=banks[3].iloc[::-1].reset_index(drop=True);return banks
    monkeypatch.setattr(module,'as_of_features',reversed_bank)
    with pytest.raises(InferenceError,match='keys/order'):predict_snapshot(processed,T,audit_models)


def test_private_row_recomputation_report_exports_and_tamper_checks(processed,audit_models,tmp_path):
    from src.asof_audit import verify_audit
    from src.asof_audit_report import write_report
    from src.baseline_audit import immutable_json,sha256
    samples=samples_with_old(processed,audit_models);specs=[m.spec() for m in audit_models]
    directory=tmp_path/'local_run';directory.mkdir()
    samples.to_parquet(directory/'samples.parquet',index=False)
    samples[KEYS+['prediction_available']+[f'p_{m.tag}' for m in audit_models]].to_parquet(directory/'predictions.parquet',index=False)
    samples.iloc[:0].to_parquet(directory/'error_cases.parquet',index=False)
    immutable_json(directory/'PREDICTIONS_FROZEN.json',{'sha256':sha256(directory/'predictions.parquet')})
    result={'run_id':'synthetic_fixture','source_kind':'synthetic_test_fixture','protocol':{'models':specs},
            'summary':summarize(samples,specs),'private_files':{name:{'sha256':sha256(directory/name)} for name in ('predictions.parquet','samples.parquet','error_cases.parquet')},
            'old_t22_label_reconciliation':'synthetic fixture checked','old_t22_probability_reconciliation':'not applicable to this renderer fixture'}
    immutable_json(directory/'RESULTS.json',result)
    assert verify_audit(directory)
    public=write_report(result,directory,tmp_path)
    assert len(pd.read_csv(public/'T30_METRICS.csv'))==12
    assert b'plotly.js' in (directory/'T30_REPORT.html').read_bytes()
    assert 'Unknown' in (tmp_path/'ASOF_AUDIT.md').read_text()
    changed=json.loads((directory/'RESULTS.json').read_text());changed['summary']['metrics'][0]['brier_score']=0.123456
    (directory/'RESULTS.json').write_text(json.dumps(changed))
    with pytest.raises(InferenceError,match='do not reproduce'):verify_audit(directory)
    (directory/'samples.parquet').write_bytes(b'tampered')
    with pytest.raises(InferenceError,match='checksum'):verify_audit(directory)

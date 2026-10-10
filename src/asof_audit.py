"""T30 fixed-model as-of audit: freeze past-only predictions before outcome/selection reads."""

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from src.asof_inference import InferenceError,NAMESPACES,as_of_features,read_model_contract
from src.baseline_audit import immutable_json,sha256
from src.evaluate import binary_metrics
from src.model_registry import ModelRegistry
from src.pipeline_cache import parquet_frames
from src.preprocessing import cached_dataset
from src.window_cohort import DAY,KEYS,row_hash
from src.window_features import WINDOW_FEATURES
from src.window_robustness import paired_uncertainty

PROTOCOL={'task':'T30','version':1,'dataset_id':'copenhagen','study_days':[24,25,26,27],'snapshot_hour':8,
          'windows':[1,3,7],'models':['historical_frequency','logistic_regression','xgboost'],
          'model_run_id':'102140b8cf3df83f','candidate_interval':'[t-1d,t)','label_interval':'(t,t+24h]',
          'known_label_rule':'observed positive OR complete sufficiently scanned absent event; otherwise Unknown',
          'prediction_rule':'common T28-valid past input across all windows/models; rejected rows retained in candidate counts',
          'label_policy':'verified common ModelContract.min_scan_coverage; never a free/default threshold',
          'classification_thresholds':'existing frozen validation-selected values, never reselected',
          'uncertainty':{'minimum_days_for_bootstrap_ci':8,'bootstrap_repetitions':1000},
          'reliability_bins':10,'high_confidence_error_cutoffs':[0.2,0.8],
          'fit_models':False,'tune_parameters':False,'test_used_for_selection':False,
          'interpretation':'post-hoc descriptive selection audit of already exposed dates, not independent external validation'}


@dataclass
class AuditModel:
    name: str
    window: int
    model: object
    contract: object
    threshold: float
    directory: Path
    evidence: Path

    @property
    def tag(self):return f'{self.name}_{self.window}d'

    def spec(self):return {'model':self.name,'window_days':self.window,'tag':self.tag,'threshold':self.threshold}


def load_audit_models(rows):
    models=[]
    for row in rows:
        contract=read_model_contract(row['directory'],evidence_path=row['evidence_path'])
        model=ModelRegistry.load(row['directory']);base=getattr(model,'base',model)
        if (row['window']!=contract.history_window_days or row['dataset_id']!=contract.dataset_id or row['model']!=model.name
            or getattr(base,'feature_contract',None)!='bounded_window_v1' or model.feature_window_days!=contract.history_window_days
            or getattr(model,'method',None)!=contract.calibration_method):
            raise InferenceError('Audit model dataset/window/feature/calibration contract mismatch.')
        models.append(AuditModel(model.name,contract.history_window_days,model,contract,float(model.threshold),Path(row['directory']),Path(row['evidence_path'])))
    if not models or {m.window for m in models}!={1,3,7} or len({m.tag for m in models})!=len(models):
        raise InferenceError('Audit requires unique frozen models covering1/3/7d.')
    if len({(m.contract.dataset_id,m.contract.time_origin_seconds,m.contract.min_scan_coverage) for m in models})!=1:
        raise InferenceError('Audit models must share dataset/time origin/verified label coverage policy.')
    return models


def predict_snapshot(processed,timestamp,models):
    """Vectorized equivalent of T28 gates on identical keys; no future rows/cohort IO."""
    contract=models[0].contract
    if NAMESPACES.get(processed.report['dataset'])!=contract.dataset_id or processed.report['time_origin_seconds']!=contract.time_origin_seconds:
        raise InferenceError('Audit source/model namespace or time origin mismatch.')
    if any(timestamp<=m.contract.information_deadline for m in models):
        raise InferenceError('model_information_conflict: audit time is not after all model label deadlines.')
    banks=as_of_features(processed,timestamp,dataset_id=contract.dataset_id,windows=(1,3,7),min_scan_coverage=contract.min_scan_coverage)
    reference=banks[1];result=reference[KEYS].copy()
    available=np.full(len(result),bool(processed.report.get('scan_coverage_available')))
    for window,bank in banks.items():
        if not bank[KEYS].equals(reference[KEYS]):raise InferenceError('Window keys/order differ.')
        scans=bank[['scan_coverage_a','scan_coverage_b']].to_numpy(dtype=float)
        available &= np.isfinite(scans).all(axis=1)&(scans>0).all(axis=1)
    result['prediction_available']=available
    result['inference_reason']=np.where(available,'valid_pre_t_inputs','missing_historical_scan_evidence')
    result['past_contact_bins_1d']=reference.pair_contact_bins.to_numpy()
    result['past_contact_count_1d']=reference.pair_contact_count.to_numpy()
    result['past_scan_min_1d']=reference[['scan_coverage_a','scan_coverage_b']].min(axis=1,skipna=False).to_numpy()
    result['past_recency_seconds_1d']=reference.recency_seconds.to_numpy()
    for entry in models:
        if entry.model.threshold!=entry.threshold:raise InferenceError('Frozen classification threshold changed.')
        values=np.full(len(result),np.nan)
        if available.any():
            X=banks[entry.window].loc[available,WINDOW_FEATURES].copy();X.attrs['history_window_days']=entry.window
            values[available]=entry.model.predict_proba(X)[:,1]
        result[f'p_{entry.tag}']=values
    return result


def reveal_snapshot(processed,timestamp,candidates,*,min_scan_coverage,backtest=False):
    """Batch T28 outcome semantics; only callable after explicit outcome authorization."""
    if backtest is not True:raise InferenceError('explicit_backtest_required')
    if not np.isfinite(min_scan_coverage) or not 0<min_scan_coverage<=1:raise InferenceError('Invalid verified coverage.')
    keys=candidates.loc[:,KEYS].copy()
    if keys.duplicated(KEYS).any() or not keys.timestamp.eq(timestamp).all():raise InferenceError('Outcome keys/time mismatch.')
    future=(ds.field('timestamp')>timestamp)&(ds.field('timestamp')<=timestamp+DAY)
    positive=set()
    for f in parquet_frames(processed.directory/'contacts.parquet',['user_min','user_max'],future):
        positive.update(f.drop_duplicates().itertuples(index=False,name=None))
    observed={};scan_reason='scan_coverage_unknown'
    if processed.report['dataset']=='Copenhagen' and processed.report.get('scan_coverage_available'):
        try:
            for f in parquet_frames(processed.directory/'observations.parquet',['timestamp','user_id','scan_observed'],future):
                for t,user,_ in f.loc[f.scan_observed.eq(True)].itertuples(index=False,name=None):
                    observed.setdefault(int(user),set()).add(int(t)//300)
            scan_reason='low_scan_coverage'
        except OSError:
            observed={};scan_reason='scan_evidence_missing'
    available=scan_reason=='low_scan_coverage'
    coverage={user:len(bins)/288 for user,bins in observed.items()}
    keys['future_scan_coverage_a']=keys.user_min.map(lambda u:coverage.get(u,0) if available else np.nan)
    keys['future_scan_coverage_b']=keys.user_max.map(lambda u:coverage.get(u,0) if available else np.nan)
    hit=np.array([(a,b) in positive for a,b in keys[['user_min','user_max']].itertuples(index=False,name=None)],dtype=bool)
    complete=timestamp+DAY<=processed.report['source_timestamp_max']-processed.report['time_origin_seconds']
    covered=(keys[['future_scan_coverage_a','future_scan_coverage_b']].min(axis=1,skipna=False)>=min_scan_coverage)&complete&available
    keys['strict_future_covered']=covered
    labels=pd.Series(pd.NA,index=keys.index,dtype='Int8');labels.loc[hit]=1;labels.loc[~hit&covered]=0
    keys['label_24h']=labels
    keys['outcome']=np.where(hit,'Contact',np.where(covered,'No Contact','Unknown'))
    keys['outcome_reason']=np.where(hit,'observed_positive_evidence',np.where(covered,'adequately_observed_no_contact',
                              'future_window_incomplete' if not complete else scan_reason))
    keys['reliable_label']=labels.notna()
    return keys


def attach_old_cohort(samples,old):
    if old.duplicated(KEYS).any():raise InferenceError('Old cohort keys are not unique.')
    old=old[KEYS+['label_24h']].rename(columns={'label_24h':'old_label_24h'})
    result=samples.merge(old,on=KEYS,how='left',validate='one_to_one',indicator=True)
    result['in_old_t22']=result._merge.eq('both')
    if result.in_old_t22.sum()!=len(old):raise InferenceError('OldT22 keys are not a subset of past-only candidates.')
    matching=result.loc[result.in_old_t22]
    if matching.label_24h.isna().any() or not matching.label_24h.astype(int).eq(matching.old_label_24h.astype(int)).all():
        raise InferenceError('Old/new labels disagree on matched keys.')
    return result.drop(columns=['_merge','old_label_24h'])


def _metrics(frame,spec):
    if frame.empty:
        return {'rows':0,'positive_rate':None,'threshold':spec['threshold'],'pr_auc_average_precision':None,'roc_auc':None,
                'brier_score':None,'log_loss':None,'precision':None,'recall':None,'f1':None,'accuracy':None,'status':'no_evaluable_rows'}
    result=binary_metrics(frame.label_24h.astype(int),frame[f"p_{spec['tag']}"],threshold=spec['threshold'])
    return {**result,'status':'both_classes' if frame.label_24h.nunique()==2 else 'single_class_descriptive_only'}


def _groups(samples):
    result=samples.copy()
    result['past_frequency_group']=np.where(result.past_contact_bins_1d<=1,'1',np.where(result.past_contact_bins_1d<=5,'2-5','>5'))
    scan=result.past_scan_min_1d
    result['past_scan_group']=np.where(scan.isna(),'unknown',np.where(scan<0.5,'below0.5',np.where(scan<0.75,'0.5-0.75','>=0.75')))
    result['prediction_day']=(result.timestamp//DAY+1).astype(str)
    return result


def _population(frame,name):
    known=frame.loc[frame.reliable_label]
    return {'population':name,'rows':len(frame),'positive':int(frame.label_24h.eq(1).sum()),'negative':int(frame.label_24h.eq(0).sum()),
            'unknown':int((~frame.reliable_label).sum()),'unknown_rate':float((~frame.reliable_label).mean()) if len(frame) else None,
            'known_label_rate':float(frame.reliable_label.mean()) if len(frame) else None,
            'positive_rate_reliable_only':float(known.label_24h.astype(int).mean()) if len(known) else None,
            'observed_positive_fraction_all_lower_bound':float(frame.label_24h.eq(1).sum()/len(frame)) if len(frame) else None,
            'past_contact_bins_mean':float(frame.past_contact_bins_1d.mean()) if len(frame) else None,
            'past_contact_bins_median':float(frame.past_contact_bins_1d.median()) if len(frame) else None,
            'past_scan_mean':float(frame.past_scan_min_1d.mean()) if frame.past_scan_min_1d.notna().any() else None}


def summarize(samples,specs):
    if samples.duplicated(KEYS).any() or not samples.reliable_label.eq(samples.label_24h.notna()).all():
        raise InferenceError('Invalid audited keys/Unknown labels.')
    common=samples.prediction_available.astype(bool)
    for spec in specs:
        p=samples.loc[common,f"p_{spec['tag']}"].to_numpy(dtype=float)
        if not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise InferenceError('Invalid common prediction probabilities.')
    masks={'reliable_predicted':common&samples.reliable_label,'strict_covered_predicted':common&samples.strict_future_covered,
           'old_t22_overlap':common&samples.in_old_t22,'added_reliable_predicted':common&samples.reliable_label&~samples.in_old_t22}
    metrics=[]
    for scope,mask in masks.items():
        for spec in specs:
            part=samples.loc[mask];values=_metrics(part,spec)
            metrics.append({'scope':scope,**spec,**values,'distinct_prediction_days':int(part.timestamp.nunique()),
                            'ap_over_scope_prevalence':values['pr_auc_average_precision']/values['positive_rate'] if values['pr_auc_average_precision'] is not None and values['positive_rate'] else None})
    daily=[]
    for t,part in samples.groupby('timestamp'):
        counts=_population(part,'all_asof')
        daily.append({'timestamp':int(t),'study_day':int(t//DAY+1),**counts,'prediction_available':int(part.prediction_available.sum()),
                      'strict_future_covered':int(part.strict_future_covered.sum()),'old_t22_rows':int(part.in_old_t22.sum()),
                      'added_rows':int((~part.in_old_t22).sum())})
    sensitivity=[];grouped=_groups(samples)
    for dimension in ('past_frequency_group','past_scan_group','prediction_day'):
        for group,part in grouped.groupby(dimension):
            for spec in specs:
                evaluable=part.loc[part.prediction_available&part.reliable_label]
                sensitivity.append({'dimension':dimension,'group':str(group),**spec,'candidate_rows':len(part),
                                    'unknown_rows':int((~part.reliable_label).sum()),'unknown_rate':float((~part.reliable_label).mean()),**_metrics(evaluable,spec)})
    reliability=[];errors=[];distribution=[]
    reliable=samples.loc[masks['reliable_predicted']]
    for spec in specs:
        p=reliable[f"p_{spec['tag']}"].to_numpy(dtype=float);y=reliable.label_24h.to_numpy(dtype=int)
        bins=np.minimum((p*10).astype(int),9)
        for b in np.unique(bins):
            mask=bins==b
            reliability.append({**spec,'bin':int(b),'rows':int(mask.sum()),'mean_probability':float(p[mask].mean()),'observed_fraction':float(y[mask].mean())})
        prediction=p>=spec['threshold']
        errors.append({**spec,'rows':len(y),'true_positive':int((prediction&(y==1)).sum()),'false_positive':int((prediction&(y==0)).sum()),
                       'true_negative':int((~prediction&(y==0)).sum()),'false_negative':int((~prediction&(y==1)).sum()),
                       'high_confidence_false_positive':int(((p>=0.8)&(y==0)).sum()),'high_confidence_false_negative':int(((p<=0.2)&(y==1)).sum())})
        for name,mask in (('all_predicted',common),('reliable_predicted',masks['reliable_predicted']),('unknown_predicted',common&~samples.reliable_label)):
            values=samples.loc[mask,f"p_{spec['tag']}"].to_numpy(dtype=float)
            distribution.append({**spec,'population':name,'rows':len(values),'mean_probability':float(values.mean()) if len(values) else None,
                                 'quantiles_0_10_50_90_100':np.quantile(values,[0,0.1,0.5,0.9,1]).tolist() if len(values) else None})
    contrasts=[]
    for name in sorted({s['model'] for s in specs}):
        first=next((s for s in specs if s['model']==name and s['window_days']==1),None)
        seventh=next((s for s in specs if s['model']==name and s['window_days']==7),None)
        if first and seventh and not reliable.empty:
            a=reliable[KEYS+['label_24h',f"p_{first['tag']}"]].rename(columns={f"p_{first['tag']}":f'p_{name}'})
            b=reliable[KEYS+['label_24h',f"p_{seventh['tag']}"]].rename(columns={f"p_{seventh['tag']}":f'p_{name}'})
            contrasts.append(paired_uncertainty(a,b,name,PROTOCOL['uncertainty']))
    return {'metrics':metrics,'daily_funnel':daily,'subgroups':sensitivity,'reliability':reliability,'errors':errors,
            'population_distributions':[_population(samples,'all_asof'),_population(samples.loc[samples.in_old_t22],'old_t22'),_population(samples.loc[~samples.in_old_t22],'added_asof')],
            'probability_distributions':distribution,'paired_descriptive_contrasts':contrasts,
            'candidates':len(samples),'prediction_available':int(common.sum()),'reliable_labels':int(samples.reliable_label.sum()),
            'unknown_labels':int((~samples.reliable_label).sum()),'distinct_prediction_days':int(samples.timestamp.nunique())}


def _frozen_inputs(root):
    run=root/'reports/window_study'/PROTOCOL['model_run_id'];rows=[];old_paths=[]
    for stage in ('T21','T22'):
        evidence=run/f'{stage}_RESULTS.json';record=json.loads(evidence.read_text())
        for window,mapping in record['model_artifacts'].items():
            for name,path in mapping.items():rows.append({'window':int(window),'model':name,'dataset_id':'copenhagen','directory':str(root/path),'evidence_path':str(evidence)})
        old_paths += [(int(w),run/item['filename'],item['sha256']) for w,item in record['predictions_local_ignored'].items()]
    return load_audit_models(rows),old_paths


def run_audit(root):
    root=Path(root).resolve();models,old_paths=_frozen_inputs(root)
    processed=cached_dataset(root/'data/raw/copenhagen/bt_symmetric.csv','Copenhagen',root/'data/processed')
    if processed is None:raise InferenceError('Missing matching genuine Copenhagen contact/scan snapshot; no implicit download or refit.')
    sources={str(p.relative_to(root)):sha256(p) for p in (processed.directory/'contacts.parquet',processed.directory/'observations.parquet',root/'data/raw/copenhagen/bt_symmetric.csv')}
    code_paths=['src/asof_audit.py','src/asof_inference.py','src/window_features.py','src/window_models.py','src/model_registry.py','src/evaluate.py']
    protocol={'protocol':PROTOCOL,'verified_label_coverage':models[0].contract.min_scan_coverage,'source_hashes':sources,
              'models':[{**m.spec(),'directory':str(m.directory.relative_to(root)),'manifest_sha256':sha256(m.directory/'manifest.json'),
                         'model_sha256':m.contract.model_sha256,'evidence_path':str(m.evidence.relative_to(root)),'evidence_sha256':sha256(m.evidence),
                         'label_information_ends':m.contract.label_information_ends} for m in models],
              'old_t22_files':[{ 'window':w,'path':str(p.relative_to(root)),'sha256':h} for w,p,h in old_paths],
              'code_hashes':{p:sha256(root/p) for p in code_paths}}
    run_id=hashlib.sha256(json.dumps(protocol,sort_keys=True).encode()).hexdigest()[:16]
    directory=root/'data/processed/asof_audit'/run_id;directory.mkdir(parents=True,exist_ok=True)
    immutable_json(directory/'PROTOCOL_FROZEN.json',{**protocol,'run_id':run_id})
    if (directory/'RESULTS.json').exists():
        verify_audit(directory)
        return json.loads((directory/'RESULTS.json').read_text()),directory
    frames=[]
    for day in PROTOCOL['study_days']:
        print(f'Past-only prediction StudyDay{day}; no future labels read',flush=True)
        frames.append(predict_snapshot(processed,(day-1)*DAY+PROTOCOL['snapshot_hour']*3600,models))
    predictions=pd.concat(frames,ignore_index=True).sort_values(KEYS).reset_index(drop=True)
    predictions.to_parquet(directory/'predictions.parquet',index=False)
    prediction_sha=sha256(directory/'predictions.parquet')
    immutable_json(directory/'PREDICTIONS_FROZEN.json',{'rows':len(predictions),'key_hash':row_hash(predictions),'sha256':prediction_sha,'future_outcomes_read':False})
    print('All predictions frozen; independently reveal future evidence',flush=True)
    revealed=[reveal_snapshot(processed,int(t),part,min_scan_coverage=models[0].contract.min_scan_coverage,backtest=True) for t,part in predictions.groupby('timestamp')]
    samples=predictions.merge(pd.concat(revealed,ignore_index=True),on=KEYS,validate='one_to_one')
    #Old cohort is consulted only now, never during candidate/feature/prediction generation.
    old=None
    for window,path,expected in old_paths:
        if sha256(path)!=expected:raise InferenceError('OldT22 prediction checksum differs.')
        frame=pd.read_parquet(path)
        cols={f'p_{name}':f'old_p_{name}_{window}d' for name in PROTOCOL['models']}
        frame=frame[KEYS+['label_24h']+list(cols)].rename(columns=cols)
        if old is None:old=frame
        else:
            if row_hash(old,labels=True)!=row_hash(frame,labels=True):raise InferenceError('Old window cohort keys/labels differ.')
            old=old.merge(frame.drop(columns='label_24h'),on=KEYS,validate='one_to_one')
    samples=attach_old_cohort(samples,old)
    if not samples.in_old_t22.eq(samples.strict_future_covered).all():raise InferenceError('Strict covered cohort no longer matches frozenT22; investigate policy before reporting.')
    overlap=samples.loc[samples.in_old_t22&samples.prediction_available].merge(old,on=KEYS,validate='one_to_one',suffixes=('','_old'))
    for m in models:np.testing.assert_allclose(overlap[f'p_{m.tag}'],overlap[f'old_p_{m.tag}'],rtol=1e-12,atol=1e-12)
    if sha256(directory/'predictions.parquet')!=prediction_sha:raise InferenceError('Frozen predictions changed during outcome/selection phase.')
    samples.to_parquet(directory/'samples.parquet',index=False)
    specs=[m.spec() for m in models];summary=summarize(samples,specs)
    #Individual error cases stay local; public exports contain aggregates only.
    error_frames=[]
    known=samples.loc[samples.prediction_available&samples.reliable_label]
    for m in models:
        wrong=known.loc[(known[f'p_{m.tag}']>=m.threshold)!=known.label_24h.astype(bool)].copy()
        wrong['audit_model']=m.tag;error_frames.append(wrong)
    pd.concat(error_frames,ignore_index=True).to_parquet(directory/'error_cases.parquet',index=False)
    if any(sha256(root/p)!=h for p,h in sources.items()):raise InferenceError('Source snapshot changed during audit.')
    result={'run_id':run_id,'source_kind':'real_public_dataset','protocol':protocol,'summary':summary,
            'private_files':{name:{'sha256':sha256(directory/name)} for name in ('predictions.parquet','samples.parquet','error_cases.parquet')},
            'prediction_frozen_before_outcomes':True,'old_t22_probability_reconciliation':'passed','old_t22_label_reconciliation':'passed',
            'all_candidate_performance_identified':False,'fit_or_tune_performed':False,
            'selection_warning':'Reliable labels depend on future observation and positive-event detection; conditional metrics are not unbiased all-candidate performance.'}
    immutable_json(directory/'RESULTS.json',result)
    verify_audit(directory)
    return result,directory


def verify_audit(directory):
    directory=Path(directory);result=json.loads((directory/'RESULTS.json').read_text())
    for filename,meta in result['private_files'].items():
        if sha256(directory/filename)!=meta['sha256']:raise InferenceError('Audit private export checksum differs.')
    frozen=json.loads((directory/'PREDICTIONS_FROZEN.json').read_text())
    if frozen['sha256']!=sha256(directory/'predictions.parquet'):raise InferenceError('Prediction freeze checksum differs.')
    samples=pd.read_parquet(directory/'samples.parquet')
    specs=[{k:m[k] for k in ('model','window_days','tag','threshold')} for m in result['protocol']['models']]
    actual=summarize(samples,specs)
    if json.dumps(actual,sort_keys=True,allow_nan=False)!=json.dumps(result['summary'],sort_keys=True,allow_nan=False):
        raise InferenceError('Metrics/funnels/groups/reliability/errors do not reproduce from private rows.')
    return True


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.cwd());parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
    if args.verify_only:
        public=json.loads((args.root/'reports/asof_audit/T30_RESULTS.json').read_text());directory=args.root/'data/processed/asof_audit'/public['run_id']
        verify_audit(directory);print('All T30 aggregate metrics reproduced from private frozen samples.');return
    result,directory=run_audit(args.root)
    from src.asof_audit_report import write_report
    write_report(result,directory,args.root)
    print(json.dumps({'run_id':result['run_id'],'candidates':result['summary']['candidates'],'known':result['summary']['reliable_labels'],
                      'unknown':result['summary']['unknown_labels'],'metrics':[r for r in result['summary']['metrics'] if r['scope']=='reliable_predicted' and r['model']=='xgboost']},indent=2),flush=True)


if __name__=='__main__':main()

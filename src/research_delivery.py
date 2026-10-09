"""T27 safe aggregate research delivery from verified local evidence; no fit/download."""

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from src.baseline_audit import sha256
from src.dataset_catalog import scan_catalog
from src.window_verify import verify_study


def build_delivery(root,config):
    root=Path(root)
    verified=verify_study(root)
    catalog=scan_catalog(root,config)
    original=json.loads((root/'reports/T17_SAFE_METADATA.json').read_text())
    study=json.loads((root/'reports/window_study/T22_ROBUSTNESS.json').read_text())
    rows=[{'experiment':'T17','window_days':14,'model':name,'dataset_id':'copenhagen','cohort':'T17 all-past known pairs','evaluation_scope':'frozen_test',**{k:v for k,v in values.items() if k!='reliability'}} for name,values in original['metrics']['test'].items()]
    rows += [{'experiment':'T21-T22','dataset_id':'copenhagen','cohort':'shared1d candidates + full7d span','evaluation_scope':'frozen_test',**r} for r in study['main_metrics']]
    pd.DataFrame(rows).to_csv(root/'reports/RESEARCH_METRICS.csv',index=False)
    payload={'source_kind':'real_public_dataset','metrics':rows,'window_run_id':study['run_id'],'T17_test_previously_exposed':True,
             'different_cohorts_not_direct_AP_comparable':True,'primary_test_days':4,'test_used_for_selection':False,
             'source_report_hashes':{name:sha256(root/name) for name in ['reports/T17_SAFE_METADATA.json','reports/window_study/T22_ROBUSTNESS.json']},
             'dataset_statuses':catalog,'verification':verified}
    (root/'reports/RESEARCH_METRICS.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (root/'reports/DATASET_CATALOG.json').write_text(json.dumps({'verified_date':'2026-10-10','datasets':catalog},ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    known=[r for r in catalog if r['dataset_id']=='reality_mining_mendeley']
    if known:(root/'reports/T25_REALITY_MINING_DIAGNOSTICS.json').write_text(json.dumps(known[0],ensure_ascii=False,indent=2)+'\n')
    text='''# Encounter Lab — Dataset Catalog

Verified:2026-10-10 (Asia/Kuala_Lumpur). Every population has a separate namespace; no identical anonymous numbers were matched across sources. No raw sources/models/individual records are committed or uploaded.

| Dataset | Access | License | Contact IDs | Event rows | Observed span(days) | Primary status |
| --- | --- | --- | --- | --- | --- | --- |
'''
    for r in catalog:
        span=f"{r['span_days']:.6f}" if r.get('span_days') is not None else 'unknown'
        text+=f"|[{r['name']}]({r['source_url']})|{r['access_status']}|{r['licence']}|{r['participants'] if r['participants'] is not None else 'unknown'}|{r['event_rows'] if r['event_rows'] is not None else 'unknown'}|{span}|{r['eligibility_status']}|\n"
    for r in catalog:
        text+=f"\n## {r['name']}\n\nSource:[publisher/source]({r['source_url']}). Citation:{r['citation']}.\n\n{r['scan_coverage_evidence']}\n\nStatus:{r['eligibility_status']}. {r['reason']}\n\n"
        if r.get('usable_days_for_1d_3d_7d'):
            text+='| History | Calendar-complete snapshots | Reliable primary snapshots | Purged date capacity train/validation/test |\n| --- | --- | --- | --- |\n'
            for w,count in r['usable_days_for_1d_3d_7d'].items():
                text+=f"|{w}d|{count['calendar_complete_snapshots']}|{count['primary_eligible_snapshots']}|{count.get('chronological_purged_date_capacity','unverified')}|\n"
        if r.get('file_hash'):text+=f"\nFile:{r['file_name']};SHA256:`{r['file_hash']}`.\n"
    text+='''
## Eligibility interpretation

Calendar span/snapshot capacity is a time-only upper bound, not scan coverage or an actual labeled cohort. Unavailable counts remain null rather than invented as zero measured contacts. eligible_primary_24h means source observation policy and purged eligible labels were checked; each study still needs its own common candidate/full-history/class/day audit. Only Copenhagen supports the reported actual predictive experiment. High School lacks reliable scan evidence and7d span. Both Workplace sources have only3 calendar-complete7d snapshots and no online logs. Reality Mining processed ticks have unknown units and many repeats. Social Evolution actual files/license/path remain unverified; published interpolation creates an additional strict-time risk.

The original MIT official endpoints failed live connection; this is not proof of restricted access. No access bypass was attempted. Mendeley CC BY4.0 applies to its processed redistribution; the mirror's site-code license was not repurposed as a data license. See reports/T25_REALITY_MINING.md and reports/T26_SOURCE_VERIFICATION.md for source dictionaries and measured limitations. Workplaces' publisher descriptions and actual timestamp extent are kept distinct; no calendar mismatch is silently repaired.

Raw files:data/raw/catalog/<dataset_id>/; local per-source dataset_manifest.json and contact Parquet:data/processed/catalog/<dataset_id>/. Existing Copenhagen/High School paths/loaders/downloads remain supported. The Dataset Catalog UI can scan, inspect, legally download verified sources, or validate manual imports. A bounded schema probe precedes a first full new-source acquisition. Imports validate before publishing and refuse to replace existing raw files. Restricted/unverified acquisition paths do not run automatically.
'''
    (root/'DATASET_CATALOG.md').write_text(text)
    metrics=pd.DataFrame([r for r in rows if r['model'] in ('xgboost','xgboost_sigmoid')])
    report='''# Encounter Lab — Research Report

Date:2026-10-10 (Asia/Kuala_Lumpur). T17–T27 research/engineering work is complete within verified source limits. The target remains recorded anonymous-device proximity in(t,t+24h], not romance, friendship, conversation or long-term relationships.

The genuine Copenhagen fixed-protocol common-cohort study found higher AP with7d than1d history in the measured periods;3d was intermediate. This is preliminary temporal evidence, not a statistical-significance, long-term, new-person or independent-external-validation claim. T17 had already exposed overlapping dates before the new study was declared.

## Actual main model evidence

| Experiment/cohort | Window | AP | ROC-AUC | Brier | Log Loss | Positive prevalence |
| --- | --- | --- | --- | --- | --- | --- |
'''
    for _,r in metrics.iterrows():report+=f"|{r['experiment']} · {r['model']}|{r['window_days']}d|{r['pr_auc_average_precision']:.6f}|{r['roc_auc']:.6f}|{r['brier_score']:.6f}|{r['log_loss']:.6f}|{r['positive_rate']:.6%}|\n"
    report+='''
T17 uses the older all-past candidate pool and14d feature bank, with769,627 eligible rows; train/validation/test269,757/155,368/260,170. Its84,332-row split loss is exactly Day16/21 purge. T18 froze its source/report/model/code evidence at f116951. New raw AP must not be compared to T17 as an identical-cohort improvement: candidate populations, history completeness and prevalence differ.

T21–T22 run102140b8cf3df83f shares strict[t-1d,t) candidates, full7d source span, exact dataset/time/pair keys and labels, original0.5 recorded-bin coverage, and strict24h chronological purge.100,485 eligible rows become54,677 train/14,816 validation/25,569 test over11/3/4 dates;5,423 boundary rows purged. No downsampling, random-row split or future features. Same seed42 and XGBoost200 trees/depth4/rate0.05; Logistic Regression and Historical Frequency also fitted at each window.3 validation dates cannot support independent calibration plus>=2 threshold dates after purge; raw probabilities/reliability are disclosed. Thresholds use validation only. Poor1d frequency probabilities remain reported.

XGBoost7d−1d AP difference:+0.102644; positive on4/4 primary test dates. Leave-one-day-out descriptive range[+0.093727,+0.112168] is not a confidence interval; only4 day blocks, below the prespecified8-day bootstrap gate. Three predeclared expanding folds produce positive differences+0.084520,+0.086919,+0.044854, but share users/pairs/training history and are not independent trials. Subgroup/date sensitivity and separate7d-candidate reach counts are available. Expanded candidate-population AP is not claimed as a pure window effect.

## Research interface and reproduction

History Window Study includes setup, cohort audit, metric/PR/reliability/date/paired-difference charts, CSV/JSON/HTML downloads and saved-model case comparisons. Default settings reuse frozen results; changed settings execute cached validation-only jobs without reopening the reported test for selection. Future case predictions read historical feature banks only; actual outcomes require explicit backtest and a matching exported target. Unsupported calibration, missing files/coverage or too few dates give specific blockers.

Dataset Catalog independently reports each source's access/license/schema/hashes/IDs/time/missingness and1/3/7d date capacity. New adapters preserve old loaders/downloaders. Dataset status outcomes appear in [DATASET_CATALOG.md](DATASET_CATALOG.md); they are not fabricated training successes. Only Copenhagen currently supports actual primary prediction metrics.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.window_verify
.venv/bin/python -m src.research_delivery
.venv/bin/streamlit run app.py
```

The research delivery command only reads/diagnoses local evidence and generates aggregate reports; it neither fits models nor downloads sources. The original local ignored artifacts are required for full frozen verification; a fresh clone must prepare lawful matching source/artifacts rather than substitute mismatched files. See WINDOW_STUDY.md for the model/cohort input contract and prior reports for exact timestamps/hashes.

## Limits and delivery boundary

Recorded symmetrized bins/50% coverage are availability proxies, not proof of continuous device presence or a guaranteed negative. Repeated participants/pairs/days and short observation/test span limit inference. Unverified calendar origin, communications, and static endpoint relationships are excluded. Missing online logs, processed time ticks and interpolated data constrain new sources. Source-specific populations/sensors are never merged for a larger apparent sample. No private/raw datasets, individual predictions, model weights, credentials or large HTML bundles enter Git; no unauthorized remote push.

Machine-readable actual metrics:reports/RESEARCH_METRICS.csv and.json. Source manifests:reports/DATASET_CATALOG.json. Standalone interactive exports stay local under the frozen run; the UI creates downloads from actual result data. Verification details and final test counts are recorded in PROGRESS.md and reports/T27_VERIFICATION.json. No more task starts automatically after T27.
'''
    (root/'RESEARCH_REPORT.md').write_text(report)
    window=(root/'reports/window_study/T22_WINDOW_COMPARISON.md').read_text()
    window+='''

## T23–T27 research edition interface

Open History Window Study in the top navigation. The default Copenhagen/coverage0.5/seed42/no-calibration configuration displays the frozen window study after Run Study verification. Changed coverage/seed/model/window settings produce separate validation-only cached jobs. New external sources are selectable for diagnosis but cannot train until observation evidence and date gates are verified. Candidate-pool expansion remains a separate reach-only analysis. No changed setting silently overwrites a frozen experiment or treats a new report as pristine test evidence.

Case Explorer selects only common historical pairs and times strictly after saved validation information deadlines. Its future mode reads no target columns; enable historical backtest explicitly for available actual outcomes. Unknown targets stay Unknown. Registry feature inputs are bounded_window_v1, with matching1/3/7d histories; legacy14d E2 banks are not substituted.

T27 verified10-page AppTest routing, actual frozen study charts/downloads/model cases, a genuine changed-seed validation job with recomputed metrics, full frozen36-model prediction equivalence, source/processed hashes and actual CSV/HTML export structure. Exact command results are in PROGRESS.md and reports/T27_VERIFICATION.json. Data/model/private predictions stay local and ignored.
'''
    (root/'WINDOW_STUDY.md').write_text(window)
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.cwd());args=parser.parse_args()
    config=yaml.safe_load((args.root/'configs/default.yaml').read_text())
    result=build_delivery(args.root,config)
    print(json.dumps({'datasets':[{k:r.get(k) for k in ('dataset_id','eligibility_status','event_rows')} for r in result['dataset_statuses']], 'verification':result['verification']},indent=2))


if __name__=='__main__':main()

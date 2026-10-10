"""Public-only audit acceptance and deliberate evidence corruption regressions."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from src.final_audit import AuditError, audit_aggregates, audit_public
from tools.check_repository_safety import FROZEN_DOCUMENTS, approved_reports

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def public_only(tmp_path):
    for name in approved_reports(ROOT)|set(FROZEN_DOCUMENTS)|{'CI_VERIFICATION.md'}:
        dest=tmp_path/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest)
    (tmp_path/'.git').write_text('gitdir: '+str(ROOT/'.git')+'\n')
    return tmp_path


def mutate(root,name,callback):
    path=root/name
    value=json.loads(path.read_text())
    callback(value)
    path.write_text(json.dumps(value))


def test_public_only_scope_and_no_private_reads(public_only,monkeypatch):
    original=Path.read_bytes
    def guarded(path):
        assert not set(path.relative_to(public_only).parts)&{'data','models'}
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',guarded)
    result=audit_aggregates(public_only)
    assert result['status']=='PASS'
    assert result['verification_scope']=='public_aggregate_verified'
    assert result['raw_reproduction']=='not_verifiable_without_local_artifacts'
    assert result['t30']['predicted_reliable']==27802
    assert result['t30']['reliable_labels']==27820
    serialized=json.dumps(result)
    assert not any(s in serialized for s in ('user_min','user_max','participant_id','prediction_probability'))
    assert not (public_only/'data').exists() and not (public_only/'models').exists()


def test_real_public_frozen_integrity():
    assert audit_public(ROOT)['frozen_files_unchanged']==51


@pytest.mark.parametrize('name,callback,location',[
    ('reports/T17_SAFE_METADATA.json',lambda d:d['split']['test'].update(positive=27820),'T17.split.test'),
    ('reports/T17_METRICS.json',lambda d:d['metrics']['test']['xgboost_sigmoid'].update(rows=25569),'T17_METRICS.rows'),
    ('reports/window_study/T22_ROBUSTNESS.json',lambda d:d['main_metrics'][0].update(rows=27802),'T22_METRICS.rows'),
    ('reports/window_study/T22_ROBUSTNESS.json',lambda d:d['paired_uncertainty'][0].update(confidence_interval=[0,1]),'T22.uncertainty'),
    ('reports/asof_audit/T30_RESULTS.json',lambda d:d['summary'].update(reliable_labels=27802),'T30.reliable_labels'),
    ('reports/asof_audit/T30_RESULTS.json',lambda d:d['summary'].update(unknown_labels=0),'T30.unknown_labels'),
    ('reports/asof_audit/T30_RESULTS.json',lambda d:d['summary']['population_distributions'][0].update(negative=30287),'T30_SELECTION_BIAS.negative'),
    ('reports/asof_audit/T30_RESULTS.json',lambda d:d.update(fit_or_tune_performed=True),'T30.scope'),
    ('reports/multisource/T31_SOURCE_SUMMARY.json',lambda d:d['sources'][-1].update(status='ready'),'social_evolution.unavailable'),
    ('reports/multisource/T31_SOURCE_SUMMARY.json',lambda d:next(s for s in d['sources'] if s['dataset_id']=='reality_mining_mendeley').update(timestamp_unit='seconds'),'MIT.unverified_time'),
])
def test_corrupt_public_evidence_rejected(public_only,name,callback,location):
    mutate(public_only,name,callback)
    with pytest.raises(AuditError,match=location):
        audit_aggregates(public_only)


@pytest.mark.parametrize('name,field,value,location',[
    ('reports/multisource/T31_RETRIEVAL_METRICS.csv','observed_positive_capture_at_k','0.9','observed_positive_capture_at_k'),
    ('reports/multisource/T31_RETRIEVAL_METRICS.csv','analysis_type','Binary Precision','analysis_type'),
    ('reports/multisource/T31_RETRIEVAL_METRICS.csv','dataset_id','social_evolution','source'),
    ('reports/performance/T32_BENCHMARK.csv','duration_reduction_pct','95','duration'),
    ('reports/performance/T32_BENCHMARK.csv','memory_reduction_pct','95','memory'),
])
def test_bad_formula_and_unavailable_source(public_only,name,field,value,location):
    import csv
    path=public_only/name
    with path.open() as f: rows=list(csv.DictReader(f))
    rows[0][field]=value
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with pytest.raises(AuditError,match=location): audit_aggregates(public_only)


def test_public_cli_without_private_files_and_with_trusted_git(public_only):
    # Git object lookup is read-only; only copied public files are available to the CLI.
    (public_only/'.git').write_text('gitdir: '+str(ROOT/'.git')+'\n')
    result=subprocess.run([sys.executable,'-m','src.final_audit','--root',str(public_only)],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0,result.stdout
    assert json.loads(result.stdout)['frozen_files_unchanged']==51
    path=public_only/'WINDOW_STUDY.md'
    path.write_text(path.read_text()+'\nchanged\n')
    result=subprocess.run([sys.executable,'-m','src.final_audit','--root',str(public_only)],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==1
    assert json.loads(result.stdout)['status']=='FAIL'


def test_missing_public_input_fails_safely(public_only):
    (public_only/'reports/T17_METRICS.json').unlink()
    result=subprocess.run([sys.executable,'-m','src.final_audit','--root',str(public_only)],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==1
    assert json.loads(result.stdout)['status']=='FAIL'
    assert 'reports/T17_METRICS.json' in json.loads(result.stdout)['reason']

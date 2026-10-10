import os
from pathlib import Path
import subprocess
import urllib.request

import pytest
import requests
import yaml

ROOT=Path(__file__).resolve().parents[1]


def test_live_http_is_refused_before_any_network():
    with pytest.raises(AssertionError,match='Live HTTP'):
        requests.get('https://example.invalid/no-download')
    with pytest.raises(AssertionError,match='Live HTTP'):
        urllib.request.urlopen('https://example.invalid/no-download')


def test_public_runner_has_no_private_data_models_runs_or_venv():
    tracked=subprocess.check_output(['git','-C',str(ROOT),'ls-files'],text=True).splitlines()
    assert all(name.endswith('/.gitkeep') for name in tracked if name.startswith(('data/','models/')))
    if os.environ.get('ENCOUNTER_CI_PUBLIC')=='1':
        assert not (ROOT/'.venv').exists()
        assert not (ROOT/'data/processed/asof_audit').exists()
        assert not (ROOT/'data/processed/multisource').exists()
        assert not any(p.is_file() and p.name!='.gitkeep' for base in ['data','models'] for p in (ROOT/base).rglob('*'))


def test_workflow_retains_complete_tests_and_minimal_read_only_permissions():
    workflow=yaml.load((ROOT/'.github/workflows/ci.yml').read_text(),Loader=yaml.BaseLoader)
    assert workflow['permissions']=={'contents':'read'}
    assert set(workflow['on'])=={'push','pull_request','workflow_dispatch'}
    assert workflow['on']['push']['branches']==['research-v2.2']
    assert workflow['on']['pull_request']['branches']==['research-v2.2']
    assert set(workflow['jobs'])=={'unit-tests','streamlit-smoke','repository-safety'}
    for job in workflow['jobs'].values():
        assert job['runs-on']=='ubuntu-latest' and int(job['timeout-minutes'])<=20
        assert 'continue-on-error' not in job
        for step in job['steps']:
            if 'uses' in step:
                assert len(step['uses'].split('@')[-1])==40
                assert 'cache' not in step.get('with',{})
            if 'run' in step:
                assert '${{' not in step['run'] and '--ignore' not in step['run'] and ' -k ' not in step['run']
    commands='\n'.join(s.get('run','') for s in workflow['jobs']['unit-tests']['steps'])
    assert 'python -m pip install -r requirements.txt' in commands
    assert 'requirements-lock.txt' not in commands
    assert 'python -m pip check' in commands
    assert any(s.get('run')=='python -m pytest -q' for s in workflow['jobs']['unit-tests']['steps'])


def test_original_test_modules_remain_in_public_checkout():
    from tools.check_repository_safety import FROZEN_BASELINE
    original=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',FROZEN_BASELINE,'tests/'],text=True).splitlines()
    assert all((ROOT/name).is_file() for name in original)

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from tools import check_repository_safety as safety


@pytest.fixture
def repository(tmp_path):
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    return tmp_path


def stage(root,name,data):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    subprocess.run(['git','-C',str(root),'add','-f','--',name],check=True)


@pytest.mark.parametrize('name,data',[
    ('data/raw/contact.csv',b'timestamp,a,b\n'),
    ('data/processed/private.json',b'{}'),
    ('data/features/features.parquet',b'PAR1'),
    ('models/weights.joblib',b'weights'),
    ('misc/weights.bin',b'weights'),
    ('config/model.json',b'{"learner":{"gradient_booster":{"weights":[1,2]}}}'),
    ('reports/safe.json',b'tree\nversion=v4\nweights=1'),
    ('.venv/config',b'private'),
    ('.env',b'LOCAL_CONFIG=private'),
    ('.streamlit/secrets.toml',b'private=true'),
    ('reports/unreviewed.json',b'{}'),
    ('reports/safe.json',b'PAR1disguised'),
    ('reports/safe.json',b'{"user_min":1,"user_max":2,"probability":0.8}'),
    ('reports/safe.csv',b'user_min,user_max,label_24h,p_xgboost\n1,2,1,0.8\n'),
    ('reports/private.html',b'<html>individual data</html>'),
    ('misc/private_predictions.csv',b'pair,probability\n'),
])
def test_actually_tracked_forbidden_files_fail(repository,monkeypatch,name,data):
    stage(repository,name,data)
    monkeypatch.setattr(safety,'approved_reports',lambda _:frozenset({'reports/safe.json','reports/safe.csv'}))
    monkeypatch.setattr(safety,'check_frozen',lambda *a:0)
    result=safety.scan_repository(repository)
    assert result['status']=='FAIL' and result['violations'][0]['path']==name


def test_index_bytes_are_scanned_including_force_added_ignored_env(repository):
    stage(repository,'.gitignore',b'.env\n')
    stage(repository,'.env',b'NEVER_PUBLISH_THIS=1')
    (repository/'.env').write_bytes(b'edited after staging')
    (repository/'untracked_file').write_bytes(b'not in Git')
    files=safety.index_files(repository)
    assert files['.env']==b'NEVER_PUBLISH_THIS=1' and 'untracked_file' not in files


@pytest.mark.parametrize('provider',['github','openai','aws','database','private-key','assignment'])
def test_inert_runtime_constructed_credential_shapes_are_rejected(provider):
    # Deterministic inert fixtures, generated only in memory; no real credential literal is committed.
    tail=hashlib.sha256(b'INERT_SYNTHETIC_SCANNER_FIXTURE_NOT_A_CREDENTIAL').hexdigest()
    values={
        'github': ''.join(['ghp_',tail[:36]]),
        'openai': ''.join(['sk-proj-',tail]),
        'aws': ''.join(['AKIA',tail[:16].upper()]),
        'database': 'postgresql'+'://fixture:'+tail+'@example.invalid/db',
        'private-key': '-----BEGIN '+'PRIVATE KEY-----',
        'assignment': 'access_token = "'+tail+'"',
    }
    issues=safety.check_content('config.txt',values[provider].encode(),frozenset())
    assert any(rule.startswith('credential-pattern:') for rule in issues)
    assert values[provider] not in json.dumps(issues)


def test_markers_aggregate_structure_size_and_personal_paths():
    assert safety.check_content('data/raw/.gitkeep',b'',frozenset())==[]
    assert safety.check_content('reports/safe.json',b'{"rows":40,"known":30,"unknown":10}',{'reports/safe.json'})==[]
    assert safety.check_content('reports/safe.csv',b'model,rows,positive_rate\nx,100,0.2\n',{'reports/safe.csv'})==[]
    assert 'oversized-file' in safety.check_content('too-big.txt',b'x'*(safety.MAX_BYTES+1),frozenset())
    path='/'+ 'Users'+'/'+ 'private-fixture-user'+'/data'
    assert 'personal-home-path' in safety.check_content('note.md',path.encode(),frozenset())
    assert 'forbidden-private-path' in safety.check_content('data/.gitkeep',b'nonempty',frozenset())


def test_historical_commit_is_trusted_not_current_index(repository,monkeypatch):
    stage(repository,'reports/frozen.json',b'{"metric":0.2}')
    stage(repository,'FROZEN.md',b'prior published evidence')
    subprocess.run(['git','-C',str(repository),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                    'commit','-qm','Synthetic baseline','--no-gpg-sign'],check=True)
    baseline=subprocess.check_output(['git','-C',str(repository),'rev-parse','HEAD'],text=True).strip()
    monkeypatch.setattr(safety,'FROZEN_BASELINE',baseline)
    monkeypatch.setattr(safety,'FROZEN_DOCUMENTS',('FROZEN.md',))
    current=safety.index_files(repository)
    assert safety.check_frozen(repository,current,baseline)==2
    stage(repository,'reports/frozen.json',b'{"metric":0.9}')
    with pytest.raises(ValueError,match='Frozen public evidence changed'):
        safety.check_frozen(repository,safety.index_files(repository),baseline)
    with pytest.raises(ValueError,match='separate reviewed authorization'):
        safety.check_frozen(repository,current,'HEAD')


def test_real_historical_public_evidence_unchanged():
    root=Path(__file__).resolve().parents[1]
    current=safety.index_files(root)
    assert safety.check_frozen(root,current)>0
    assert all(name.startswith('reports/') for name in safety.approved_reports(root))


def test_gitleaks_exceptions_only_cover_known_frozen_digest_lines():
    import re
    import tomllib
    root=Path(__file__).resolve().parents[1]
    config=tomllib.loads((root/'.gitleaks.toml').read_text())
    assert config['extend']['useDefault'] is True
    assert len(config['rules'])==1 and config['rules'][0]['id']=='generic-api-key'
    allow=config['rules'][0]['allowlists'][0]
    assert allow['condition']=='AND' and allow['regexTarget']=='line'
    assert 'commits' not in allow and 'stopwords' not in allow
    assert all(not re.search(p,'unrelated.json') for p in allow['paths'])
    assert all(not re.search(p,'"api_key": "'+'a'*64+'"') for p in allow['regexes'])
    assert all(not re.search(p,'"key_hash": "'+'0'*64+'"') for p in allow['regexes'])

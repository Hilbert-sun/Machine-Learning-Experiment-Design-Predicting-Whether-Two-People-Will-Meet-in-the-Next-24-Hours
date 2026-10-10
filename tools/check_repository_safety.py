"""Scan actual Git index bytes and compare frozen evidence with a trusted historic commit.

Standard library only. Diagnostics never print candidate credentials or private rows.
"""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

FROZEN_BASELINE = '5f3be86bebe089af5dea9b671ce25fe8e0c279f0'
MAX_BYTES = 1024 * 1024
FROZEN_DOCUMENTS = ('RESEARCH_REPORT.md', 'WINDOW_STUDY.md', 'ASOF_INFERENCE.md', 'TIME_MACHINE.md',
                    'ASOF_AUDIT.md', 'MULTISOURCE_STUDY.md', 'PERFORMANCE_AUDIT.md')
PRIVATE_FIELDS = {'user_id', 'participant_id', 'user_min', 'user_max', 'user_a', 'user_b', 'pair_id',
                  'person_a', 'person_b', 'label_24h', 'prediction_probability', 'p_xgboost', 'p_logistic_regression'}
FORBIDDEN_EXTENSIONS = {'.parquet', '.joblib', '.pkl', '.pickle', '.sqlite', '.sqlite3', '.db', '.h5', '.hdf5',
                        '.pt', '.pth', '.onnx', '.safetensors', '.npy', '.npz', '.bin', '.ubj', '.bst', '.model', '.cbm',
                        '.pem', '.key', '.html', '.htm'}
SECRET_PATTERNS = {
    'github-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{60,255})\b'),
    'openai-style-key': re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}\b'),
    'aws-access-id': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'google-api-key': re.compile(r'\bAIza[A-Za-z0-9_-]{35}\b'),
    'slack-token': re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'credential-assignment': re.compile(r'''(?im)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|password)\s*[:=]\s*["']([A-Za-z0-9+/_.=-]{20,})["']'''),
    'database-password': re.compile(r'\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s:/]+:[^\s/@]+@'),
}
PERSONAL_PATH = re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+/')


def git(root, *args, input=None):
    return subprocess.check_output(['git', '-C', str(root), *args], input=input)


def index_files(root):
    records = []
    for record in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not record:
            continue
        metadata, name = record.split(b'\t', 1)
        mode, oid, stage = metadata.decode().split()
        if stage != '0' or mode not in {'100644', '100755'}:
            raise ValueError('Unmerged, symlink or unsupported Git index entry; resolve before scanning.')
        records.append((name.decode('utf-8'), oid))
    # One cat-file process, bounded by the size check in the batch headers.
    proc = subprocess.Popen(['git', '-C', str(root), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    result = {}
    try:
        for name, oid in records:
            proc.stdin.write((oid+'\n').encode()); proc.stdin.flush()
            header = proc.stdout.readline().decode().split()
            if len(header)!=3 or header[1]!='blob':
                raise ValueError('Git index references an unreadable non-blob object.')
            size = int(header[2])
            if size > MAX_BYTES:
                raise ValueError('Tracked file exceeds reviewed size limit: '+name)
            result[name] = proc.stdout.read(size)
            if proc.stdout.read(1)!=b'\n':
                raise ValueError('Invalid Git object stream.')
    finally:
        proc.stdin.close();proc.stdout.close();proc.wait(timeout=10)
    return result


def approved_reports(root, baseline=FROZEN_BASELINE):
    text = git(root, 'show', baseline+':.gitignore').decode()
    return frozenset(line[1:] for line in text.splitlines() if line.startswith('!reports/')
                     and not any(c in line for c in '*?[]') and not line.endswith('/'))


def _private_structure(value):
    if isinstance(value, dict):
        return any(str(k).lower() in PRIVATE_FIELDS|{'learner','gradient_booster','gbtree_model_param'} or _private_structure(v) for k,v in value.items())
    if isinstance(value, list):
        return any(_private_structure(v) for v in value)
    return False


def check_content(name, content, allow_reports):
    problems = []
    path = PurePosixPath(name)
    marker = path.name=='.gitkeep' and content==b''
    if (path.parts[0] in {'data','models'} and not marker) or path.parts[0] in {'.venv','venv','secrets','credentials'}:
        problems.append('forbidden-private-path')
    if name=='.streamlit/secrets.toml' or path.name=='.env' or (path.name.startswith('.env.') and path.name!='.env.example'):
        problems.append('credential-file')
    if path.suffix.lower() in FORBIDDEN_EXTENSIONS:
        problems.append('forbidden-artifact-extension')
    if content.startswith((b'PAR1', b'\x80\x04', b'\x80\x05', b'SQLite format 3', b'\x89HDF', b'tree\nversion=')):
        problems.append('disguised-binary-artifact')
    if len(content)>MAX_BYTES:
        problems.append('oversized-file')
    is_report=path.parts[0]=='reports'
    if is_report and not marker and name not in allow_reports:
        problems.append('unreviewed-report')
    if path.suffix.lower()=='.csv' and not is_report:
        problems.append('unreviewed-csv-artifact')
    try:
        text=content.decode('utf-8')
    except UnicodeDecodeError:
        return problems+['unreviewed-binary-content']
    if '\0' in text:
        problems.append('binary-content-in-text-file')
    if PERSONAL_PATH.search(text):
        problems.append('personal-home-path')
    for rule,pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            problems.append('credential-pattern:'+rule)
    if path.suffix.lower()=='.json':
        try:
            value=json.loads(text)
            if _private_structure(value):
                problems.append('private-sample-structure')
        except (ValueError, TypeError):
            problems.append('invalid-json')
    if is_report and path.suffix.lower()=='.csv':
        try:
            rows=list(csv.reader(io.StringIO(text),strict=True))
            if not rows or set(s.lower() for s in rows[0]) & PRIVATE_FIELDS:
                problems.append('private-or-empty-report-csv')
            elif any(len(row)!=len(rows[0]) for row in rows[1:]):
                problems.append('invalid-report-csv')
        except csv.Error:
            problems.append('invalid-report-csv')
    return problems


def check_frozen(root, current, baseline=FROZEN_BASELINE):
    if baseline!=FROZEN_BASELINE:
        raise ValueError('Changing the trusted frozen baseline requires separate reviewed authorization.')
    names=git(root,'ls-tree','-r','--name-only',baseline,'reports/').decode().splitlines()
    names=[n for n in names if not n.endswith('/.gitkeep')]+list(FROZEN_DOCUMENTS)
    for name in names:
        expected=git(root,'show',baseline+':'+name)
        if name not in current or hashlib.sha256(current[name]).digest()!=hashlib.sha256(expected).digest():
            raise ValueError('Frozen public evidence changed: '+name)
    return len(names)


def scan_repository(root):
    current=index_files(root)
    allowed=approved_reports(root)
    violations=[{'path':name,'rules':issues} for name,data in current.items() if (issues:=check_content(name,data,allowed))]
    if violations:
        return {'status':'FAIL','tracked_files':len(current),'violations':violations}
    count=check_frozen(root,current)
    return {'status':'PASS','tracked_files':len(current),'approved_reports':len(allowed),'frozen_files_unchanged':count,
            'trusted_baseline':FROZEN_BASELINE,'scope':'Git index blobs; built-in patterns plus separate Gitleaks full-history/index scans; not formal anonymity'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.cwd());args=parser.parse_args()
    try:
        result=scan_repository(args.root)
        print(json.dumps(result,indent=2))
        raise SystemExit(0 if result['status']=='PASS' else 1)
    except (ValueError,subprocess.CalledProcessError) as exc:
        print(json.dumps({'status':'FAIL','reason':str(exc)}))
        raise SystemExit(1)

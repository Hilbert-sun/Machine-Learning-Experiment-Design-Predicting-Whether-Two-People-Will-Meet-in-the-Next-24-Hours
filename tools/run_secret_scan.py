"""Pinned upstream Gitleaks; redact findings, scan all local history and exact Git index."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import tempfile
import urllib.request

VERSION='8.30.1'
ARCHIVES={
    ('Linux','x86_64'):('linux_x64','551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb'),
    ('Darwin','arm64'):('darwin_arm64','b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5'),
}


def install(directory):
    artifact,expected=ARCHIVES[(platform.system(),platform.machine())]
    url=f'https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/gitleaks_{VERSION}_{artifact}.tar.gz'
    with urllib.request.urlopen(url,timeout=60) as response:
        payload=response.read(20*1024*1024+1)
    if len(payload)>20*1024*1024 or hashlib.sha256(payload).hexdigest()!=expected:
        raise ValueError('Pinned Gitleaks release checksum/size verification failed.')
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
        member=archive.getmember('gitleaks')
        if not member.isfile():
            raise ValueError('Release contains no regular Gitleaks executable.')
        binary=Path(directory)/'gitleaks'
        binary.write_bytes(archive.extractfile(member).read());binary.chmod(0o700)
    return binary


def scan(root, binary):
    root=Path(root).resolve()
    config=root/'.gitleaks.toml'
    assert subprocess.check_output([str(binary),'version'],text=True).strip()==VERSION
    common=['--no-banner','--redact','--exit-code','1','--config',str(config)]
    # No license key/token or baseline suppression. Only documented exact scientific SHA exceptions.
    with tempfile.TemporaryDirectory(prefix='encounter-gitleaks-selftest-') as directory:
        path=Path(directory)/'reports/window_study/T21_RESULTS.json';path.parent.mkdir(parents=True)
        value=''.join(['ghp_',hashlib.sha256(b'INERT_SYNTHETIC_GITLEAKS_FIXTURE_NOT_A_CREDENTIAL').hexdigest()[:36]])
        path.write_text(json.dumps({'api_key':value}))
        report=Path(directory)/'selftest-findings.json'
        probe=subprocess.run([str(binary),'dir',*common,'--report-format','json','--report-path',str(report),directory],capture_output=True,text=True)
        findings=json.loads(report.read_text()) if report.is_file() else []
        if probe.returncode!=1 or not any(f.get('RuleID')=='github-pat' for f in findings):
            raise ValueError('Gitleaks self-test failed: risky runtime fixture was not rejected.')
    subprocess.run([str(binary),'git',*common,'--log-opts=--all',str(root)],check=True)
    from tools.check_repository_safety import index_files
    current=index_files(root)
    with tempfile.TemporaryDirectory(prefix='encounter-gitleaks-index-') as directory:
        for name,data in current.items():
            path=Path(directory)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        subprocess.run([str(binary),'dir',*common,directory],check=True)
    return {'status':'PASS','scanner':'gitleaks','version':VERSION,'scopes':['all available Git history','exact staged/tracked Git index'],
            'redacted':True,'online_credential_validation':False,'risky_fixture_selftest':'rejected as required'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path.cwd());parser.add_argument('--binary',type=Path);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='encounter-gitleaks-bin-') as directory:
        binary=args.binary or install(directory)
        print(json.dumps(scan(args.root,binary),indent=2))

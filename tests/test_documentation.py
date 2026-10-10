"""Validate delivered navigation, executable usage and research claim provenance."""
import ast
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

import pytest

from tools.check_repository_safety import approved_reports, check_content

ROOT=Path(__file__).resolve().parents[1]
DOCS=('README.md','FINAL_RESEARCH_AUDIT.md','REPRODUCIBILITY.md','PORTFOLIO_GUIDE.md',
      'DEMO_GUIDE.md','FINAL_RELEASE_CHECKLIST.md','CI_VERIFICATION.md','DEVELOPMENT_HISTORY.md')


@pytest.mark.parametrize('name',DOCS)
def test_document_local_links_exist(name):
    text=(ROOT/name).read_text()
    # This project uses inline Markdown links; nested badge URLs are external.
    for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)',text):
        target=target.strip('<>')
        if urlsplit(target).scheme or target.startswith('#'):
            continue
        path=unquote(target.split('#',1)[0].split('?',1)[0])
        assert (ROOT/path).is_file(),f'{name}: missing target {path}'


@pytest.mark.parametrize('name',DOCS)
def test_public_docs_pass_existing_safety_policy(name):
    assert not check_content(name,(ROOT/name).read_bytes(),approved_reports(ROOT))


def test_readme_navigation_matches_actual_router():
    tree=ast.parse((ROOT/'src/ui.py').read_text())
    pages=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
               and any(isinstance(t,ast.Name) and t.id=='PAGES' for t in n.targets))
    readme=(ROOT/'README.md').read_text()
    paths=re.findall(r'\]\((pages/[^)]+)\)',readme)
    assert paths==[path for path,_ in pages]
    assert len(paths)==12


def test_readme_real_metric_table_matches_frozen_values():
    rows=json.loads((ROOT/'reports/window_study/T22_ROBUSTNESS.json').read_text())['main_metrics']
    text=(ROOT/'README.md').read_text()
    for row in rows:
        if row['model']=='xgboost':
            line=next(line for line in text.splitlines() if line.startswith('| T22 fixed cohort, '+str(row['window_days'])+'d history'))
            cells=[c.strip() for c in line.strip('|').split('|')]
            assert cells[-3:]==[f'{row[k]:.6f}' for k in ('pr_auc_average_precision','roc_auc','brier_score')]
    assert 'not a same-population model improvement' in text
    assert 'Only four principal test dates' in text


def test_demo_and_reproduction_preserve_independent_reveal_and_empty_states():
    reproduction=(ROOT/'REPRODUCIBILITY.md').read_text()
    demo=(ROOT/'DEMO_GUIDE.md').read_text()
    assert 'Select → Predict → Freeze → Reveal' in reproduction
    assert 'Predict → Freeze → Reveal' in demo
    assert 'no standalone UI tab' in reproduction
    assert 'no dedicated navigation page' in demo
    assert 'Static Copenhagen archives cannot pass real-time prospective mode' in reproduction
    assert 'synthetic fixture' in demo and 'Unknown' in demo
    assert 'No screenshots or per-sample demo files' in demo
    # Check documented read-only CLI flags actually exist; do not invoke fitting entry points.
    assert "'--verify-only'" in (ROOT/'src/asof_audit.py').read_text()
    assert 'Case Explorer Reveal reuses the verified Time Machine policy service' in reproduction
    assert 'python -m src.window_verify' in reproduction
    assert 'python -m src.asof_audit --verify-only' in reproduction


def test_current_status_and_ci_security_policy_not_weakened():
    tasks=(ROOT/'TASKS.md').read_text()
    row=next(r for r in tasks.splitlines() if '| T34 |' in r)
    assert '| DONE |' in row and '| IN_PROGRESS |' not in row
    baseline='ae623111871407a74185777f4d3a74c642b0dcde'
    for name in ('.github/workflows/ci.yml','.gitleaks.toml','tools/check_repository_safety.py',
                 'tools/run_secret_scan.py','tests/test_repository_safety.py','tests/conftest.py'):
        expected=subprocess.check_output(['git','-C',str(ROOT),'show',baseline+':'+name])
        assert (ROOT/name).read_bytes()==expected,name

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
REVIEWED_SAFETY_ADDITIONS={
    'tools/check_repository_safety.py':(b"# Exact, human-reviewed public media (user-authorized 2026-10-28). Each entry pins one path to one\n# SHA256 and a GIF signature; any other binary content is still rejected.\nREVIEWED_MEDIA = {'docs/media/demo.gif': '41cdeb143013a986ed9a2989d6de73e635cc2dc27eae3c76e13b3dab43c99e90'}\n",
        b"    if name in REVIEWED_MEDIA:\n        if (hashlib.sha256(content).hexdigest()!=REVIEWED_MEDIA[name] or not content.startswith((b'GIF87a', b'GIF89a'))\n                or len(content)>MAX_BYTES):\n            return ['unreviewed-media-change']\n        return []\n"),
    'tests/test_repository_safety.py':(b"\n\ndef test_only_the_exact_reviewed_demo_gif_is_allowed():\n    root=Path(__file__).resolve().parents[1]\n    gif=(root/'docs/media/demo.gif').read_bytes()\n    assert safety.check_content('docs/media/demo.gif',gif,frozenset())==[]\n    assert safety.check_content('docs/media/demo.gif',gif+b'x',frozenset())==['unreviewed-media-change']\n    assert safety.check_content('docs/media/demo.gif',b'GIF89a'+b'\\x00'*10,frozenset())==['unreviewed-media-change']\n    assert 'unreviewed-binary-content' in safety.check_content('docs/media/other.gif',gif,frozenset())\n    assert set(safety.REVIEWED_MEDIA)=={'docs/media/demo.gif'}\n",),
}
DOCS=('README.md','README.en.md',*('docs/'+name for name in ('FINAL_RESEARCH_AUDIT.md','REPRODUCIBILITY.md','PORTFOLIO_GUIDE.md',
      'DEMO_GUIDE.md','FINAL_RELEASE_CHECKLIST.md','CI_VERIFICATION.md','DEVELOPMENT_HISTORY.md','PRODUCT_PLAN.md','EXPLORE_GUIDE.md','PRODUCT_DELIVERY.md')))


@pytest.mark.parametrize('name',DOCS)
def test_document_local_links_exist(name):
    text=((ROOT/name).read_text())
    # This project uses inline Markdown links; nested badge URLs are external.
    for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)',text):
        target=target.strip('<>')
        if urlsplit(target).scheme or target.startswith('#'):
            continue
        path=unquote(target.split('#',1)[0].split('?',1)[0])
        assert ((ROOT/name).parent/path).is_file(),f'{name}: missing target {path}'


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
    assert len(paths)==15
    assert paths[12]=="pages/12_Chance_Encounter.py"
    assert paths[13]=="pages/13_Encounter_Insights.py"
    assert paths[14]=="pages/14_Research_Hub.py"


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
    reproduction=(ROOT/'docs/REPRODUCIBILITY.md').read_text()
    demo=(ROOT/'docs/DEMO_GUIDE.md').read_text()
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
        current=(ROOT/name).read_bytes()
        # The only user-authorized change (2026-10-28): the exact hash-pinned demo GIF exception.
        for addition in REVIEWED_SAFETY_ADDITIONS.get(name,()):
            assert current.count(addition)==1,name
            current=current.replace(addition,b'')
        assert current==expected,name


def test_english_readme_mirrors_chinese_metrics_and_cross_links():
    zh=(ROOT/'README.md').read_text(); en=(ROOT/'README.en.md').read_text()
    assert '[English](README.en.md)' in zh and '[中文](README.md)' in en
    rows=lambda text:[line for line in text.splitlines() if line.startswith(('| T17 ','| T22 ','| T30 '))]
    assert rows(en)==rows(zh) and len(rows(en))==5
    for marker in ('Only four principal test dates','not a same-population model improvement','hjm59payrde6ronekgiqsn.streamlit.app'):
        assert marker in en


def test_license_is_official_gpl3_and_scoped_to_code():
    import hashlib
    assert hashlib.sha256((ROOT/'LICENSE').read_bytes()).hexdigest()=='3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986'
    assert '[GNU GPL-3.0](LICENSE)' in (ROOT/'README.md').read_text() and '不覆盖第三方数据' in (ROOT/'README.md').read_text()
    assert 'not third-party data' in (ROOT/'README.en.md').read_text()

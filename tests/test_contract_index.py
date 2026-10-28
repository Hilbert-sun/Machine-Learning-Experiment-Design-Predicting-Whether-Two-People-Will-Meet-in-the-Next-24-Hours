"""Every binding contract keeps its section and points at tests that actually exist."""
import ast
import json
from pathlib import Path
import re

from tools.check_repository_safety import FROZEN_DOCUMENTS, _private_structure

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / 'docs/CONTRACTS.md'
SECTIONS = (
    'Prediction data contract', 'Research window contract (T18–T22)', 'Research edition delivery (T23–T27)',
    'T28 as-of inference contract', 'T29 Time Machine contract', 'T29-FIX label coverage contract',
    'T30 audit interpretation', 'T31 multi-source exploration contract', 'T32 performance/cache/snapshot contract',
    'T33 public CI and repository integrity', 'T35 rolling-origin contract', 'T36 Hawkes contract',
    'T37 Hawkes-feature contract', 'Documentation layout (DOCS-PRESENT)', 'Online demo boundary (DEMO-DEPLOY)',
    'T38 participant-holdout contract', 'T39 day-analysis contract', 'T40 wide Hawkes-grid contract',
    'Report v2 (REPORT-UPDATE)', 'License',
)


def sections():
    text = CONTRACTS.read_text()
    return {block.splitlines()[0][3:].strip(): block for block in re.split(r'(?m)^(?=## )', text)[1:]}


def test_no_contract_section_dropped_and_agents_requires_reading_them():
    assert set(SECTIONS) <= set(sections())
    agents = (ROOT / 'AGENTS.md').read_text()
    assert '`docs/CONTRACTS.md`' in agents and 'every rule there is binding' in agents


def test_every_section_names_existing_enforcing_tests():
    for name, block in sections().items():
        line = next((l for l in block.splitlines() if l.startswith('Enforced by:')), None)
        assert line, f'{name}: no Enforced by line'
        for path, function in re.findall(r'`tests/([\w]+\.py)::(\w+)`', line):
            tree = ast.parse((ROOT / 'tests' / path).read_text())
            names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
            assert function in names, f'{name}: missing tests/{path}::{function}'
        assert re.search(r'`tests/', line) or line.startswith('Enforced by: review'), name


def test_public_study_aggregates_carry_no_private_fields():
    files = sorted((ROOT / 'studies').rglob('*.json'))
    assert len(files) >= 6
    for path in files:
        text = path.read_text()
        value = json.loads(text)
        assert not _private_structure(value), path
        assert not re.search(r'"[a-z_]*key[a-z_]*"\s*:', text), path  # hash names must not look like credentials
        protocol = value['protocol']
        assert protocol.get('test_used_for_selection') is False or protocol.get('selection') is False, path


def test_frozen_documents_stay_at_repository_root():
    for name in FROZEN_DOCUMENTS + ('DATASET_CATALOG.md',):
        assert (ROOT / name).is_file(), name

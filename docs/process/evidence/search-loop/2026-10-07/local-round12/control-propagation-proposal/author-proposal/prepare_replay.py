"""Prepare isolated normal-import replay; no app imports or Git/network actions."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
REPO = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
CHANGED = [
    'backend/app/adapters/search/retrieval.py',
    'backend/tests/test_hybrid_retrieval.py',
    'backend/tests/test_search_layer_budget_fixes.py',
]


def digest(p):
    b = p.read_bytes()
    return {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}


pins = {}
for p in sorted((REPO / 'backend/app').rglob('*')):
    if not p.is_file() or p.suffix not in {'.py', '.json'} or '__pycache__' in p.parts:
        continue
    # Source/module JSON only, not corpus pages/gold/evaluation or private data.
    rel = str(p.relative_to(REPO))
    if '/corpus/pages/' in rel:
        continue
    pins[rel] = digest(p)
    for mode in ('off', 'on'):
        d = HERE / 'replay' / mode / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, d)
for rel in ('backend/tests/conftest.py', 'backend/pytest.ini', 'backend/ruff.toml'):
    pins[rel] = digest(REPO / rel)
    for mode in ('off', 'on'):
        d = HERE / 'replay' / mode / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, d)
for rel in CHANGED:
    for mode in ('off', 'on'):
        # Both modes test the identical proposed regression files. Only native
        # retrieval differs; OFF includes the unchanged current native source.
        src = HERE / 'proposed' / rel
        if mode == 'off' and rel.startswith('backend/app/'):
            src = HERE / 'original' / rel
        d = HERE / 'replay' / mode / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, d)

patch = ''
comparisons = {}
for rel in CHANGED:
    old = (HERE / 'original' / rel).read_text()
    new = (HERE / 'proposed' / rel).read_text()
    patch += ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                        fromfile='a/' + rel, tofile='b/' + rel))
    if '/tests/' in rel:
        original_nodes = {getattr(n, 'name', ''): ast.dump(n, include_attributes=False)
                          for n in ast.parse(old).body
                          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        proposed_nodes = {getattr(n, 'name', ''): ast.dump(n, include_attributes=False)
                          for n in ast.parse(new).body
                          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        assert all(proposed_nodes.get(k) == v for k, v in original_nodes.items()), rel
        comparisons[rel] = {'existing_definitions_preserved': len(original_nodes),
                            'new_definitions': sorted(proposed_nodes.keys() - original_nodes.keys()),
                            'proposed_sha256': digest(HERE / 'proposed' / rel)}
(HERE / 'control-propagation.patch').write_text(patch)
(HERE / 'test-body-compatibility.json').write_text(json.dumps(comparisons, indent=2) + '\n')
(HERE / 'dependency-before.json').write_text(json.dumps(pins, indent=2) + '\n')
(HERE / 'replay-source-manifest.json').write_text(json.dumps({
    mode: {str(p.relative_to(HERE / 'replay' / mode)): digest(p)
           for p in sorted((HERE / 'replay' / mode).rglob('*')) if p.is_file()}
    for mode in ('off', 'on')
}, indent=2) + '\n')
print(json.dumps({'dependencies': len(pins), 'patch': digest(HERE / 'control-propagation.patch'),
                  'existing_test_definitions_preserved': True}))

"""Finite stdlib-only compatibility audit; does not import application code."""

import ast
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = ROOT / 'work/ashyq-apply'
OWN = Path(__file__).resolve().parent
STOP = ROOT / 'work/local-round7/provider-STOP.json'
STOP_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state():
    pin = ROOT / 'work/local-round13/root-stopped-trace-accounting/source-before-999.json'
    mapping = json.loads(pin.read_text())['file_sha256']
    previous = json.loads((ROOT / 'work/local-round12/root-control-propagation/source-after-999.json').read_text())['file_sha256']
    mismatches = [rel for rel, digest in mapping.items() if sha(REPO / rel) != digest]
    assert len(mapping) == 999 and mapping == previous and not mismatches
    assert sha(STOP) == STOP_SHA
    return {'source_map': str(pin), 'source_map_sha256': sha(pin), 'selected_source_count': len(mapping), 'previous_map_equal': mapping == previous, 'physical_mismatches': mismatches, 'STOP_sha256': sha(STOP)}


def qualified(node, parents):
    names = [node.name]
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
    return '.'.join(reversed(names))


def row(path, node, parents):
    return {'file': str(path.relative_to(REPO)), 'line': node.lineno, 'end_line': node.end_lineno, 'scope': qualified(node, parents), 'signature': ast.unparse(node.args), 'accepts_kwargs': node.args.kwarg is not None, 'source_sha256': sha(path)}


def audit():
    before = state()
    defs, calls, patches, subclasses, excerpts = [], [], [], [], []
    for base in ['backend/app', 'backend/tests', 'backend/evaluation', 'backend/scripts']:
        for path in sorted((REPO / base).rglob('*.py')):
            source = path.read_text()
            if not any(token in source for token in ['_discover_one', 'LiveDiscoveryAdapter', 'CatalogueDiscoveryAdapter']):
                continue
            tree = ast.parse(source)
            parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
            lines = source.splitlines()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == '_discover_one':
                    defs.append(row(path, node, parents))
                elif isinstance(node, ast.ClassDef) and any(ast.unparse(base).split('.')[-1] in ['LiveDiscoveryAdapter', 'CatalogueDiscoveryAdapter'] for base in node.bases):
                    subclasses.append({'file': str(path.relative_to(REPO)), 'line': node.lineno, 'class': node.name, 'bases': [ast.unparse(base) for base in node.bases], 'overrides_discover_one': any(isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == '_discover_one' for child in node.body)})
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == '_discover_one':
                        calls.append({'file': str(path.relative_to(REPO)), 'line': node.lineno, 'call': ast.unparse(node), 'source_sha256': sha(path)})
                    if isinstance(node.func, ast.Attribute) and node.func.attr == 'setattr' and len(node.args) >= 3 and isinstance(node.args[1], ast.Constant) and node.args[1].value == '_discover_one':
                        enclosing = node
                        while enclosing in parents and not isinstance(enclosing, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            enclosing = parents[enclosing]
                        target = node.args[2]
                        matches = [candidate for candidate in ast.walk(enclosing) if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)) and isinstance(target, ast.Name) and candidate.name == target.id]
                        assert len(matches) == 1
                        mock = matches[0]
                        item = row(path, mock, parents)
                        item.update({'monkeypatch_line': node.lineno, 'target': ast.unparse(node.args[0]), 'mock': ast.unparse(target)})
                        patches.append(item)
                        excerpts.append({'kind': 'existing_mock_body', **item, 'source': '\n'.join(lines[mock.lineno - 1:mock.end_lineno]) + '\n'})
    assert len(defs) == 1 and len(patches) == 6 and all(r['accepts_kwargs'] for r in patches)
    assert len(calls) == 3 and all(not r['overrides_discover_one'] for r in subclasses)

    targets = {
        'backend/app/adapters/discovery/live_discovery.py': {'DiscoveryTrace', 'LiveDiscoveryAdapter.discover', 'LiveDiscoveryAdapter._discover_one', 'LiveDiscoveryAdapter._apply'},
        'backend/app/catalogue/discovery.py': {'CatalogueDiscoveryAdapter.discover', 'CatalogueDiscoveryAdapter._enrich', 'CatalogueDiscoveryAdapter._identify_site'},
        'backend/scripts/canary_discovery.py': {'_gather_report'},
    }
    for rel, wanted in targets.items():
        path = REPO / rel
        source = path.read_text()
        tree = ast.parse(source)
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and qualified(node, parents) in wanted:
                text = ast.get_source_segment(source, node)
                excerpts.append({'kind': 'native_scope', 'file': rel, 'scope': qualified(node, parents), 'line': node.lineno, 'end_line': node.end_lineno, 'file_sha256': sha(path), 'source': text, 'excerpt_utf8_sha256': hashlib.sha256(text.encode()).hexdigest()})

    evidence = {'time': datetime.now(UTC).isoformat(), 'audit': 'stdlib AST inventory only; no application methods or tests executed', 'before': before, 'definitions': defs, 'calls': calls, 'monkeypatches': patches, 'direct_subclasses': subclasses, 'signature_findings': {'native_definition_count': len(defs), 'native_and_test_call_count': len(calls), 'existing_monkeypatch_count': len(patches), 'all_existing_mocks_accept_kwargs': all(r['accepts_kwargs'] for r in patches), 'no_existing_subclass_override': all(not r['overrides_discover_one'] for r in subclasses)}, 'after': state(), 'exclusions': ['Not an SQL/fence proof', 'No provider/Fetcher/test execution', 'No claim of finite peer coverage before immutable proposal arrives']}
    (OWN / 'inventory.original.json').write_text(json.dumps(evidence, indent=2) + '\n')
    (OWN / 'source-excerpts.original.json').write_text(json.dumps(excerpts, indent=2) + '\n')
    print(json.dumps({'definitions': len(defs), 'calls': len(calls), 'mocks': len(patches), 'subclasses': len(subclasses), 'source999_unchanged': True, 'STOP_unchanged': True, 'application_imports': 0, 'executed_native_cases': 0}))


if __name__ == '__main__':
    audit()

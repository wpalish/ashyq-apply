"""Verify frozen author packet and native minimal delta before any app import."""

import ast
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

OWN = Path(__file__).resolve().parent
ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = ROOT / 'work/ashyq-apply'
B = OWN / 'frozen-b'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def definitions(tree):
    result = {}
    def walk(nodes, prefix=''):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + node.name
                if isinstance(node, ast.ClassDef):
                    walk(node.body, name + '.')
                else:
                    result[name] = ast.dump(node, include_attributes=False)
    walk(tree.body)
    return result


def main():
    expected = json.loads((ROOT / 'work/local-round13/root-stopped-trace-accounting/source-before-999.json').read_text())['file_sha256']
    assert len(expected) == 999 and all(sha(REPO / p) == digest for p, digest in expected.items())
    assert sha(ROOT / 'work/local-round7/provider-STOP.json') == '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
    source = json.loads((B / 'source-manifest.json').read_text())
    assert all(sha(B / 'original' / p) == row['sha256'] == sha(REPO / p) for p, row in source['original'].items())
    delta = {}
    for rel in source['proposed']:
        before = (B / 'original' / rel).read_text()
        after = (B / 'proposed' / rel).read_text()
        old = definitions(ast.parse(before))
        new = definitions(ast.parse(after))
        delta[rel] = {'changed': sorted(k for k in old if old[k] != new.get(k)), 'removed': sorted(set(old) - set(new)), 'added': sorted(set(new) - set(old)), 'original_sha256': sha(B / 'original' / rel), 'proposed_sha256': sha(B / 'proposed' / rel)}
        assert not delta[rel]['removed']
        if rel.startswith('backend/tests/'):
            assert after.startswith(before) and not delta[rel]['changed']
            delta[rel]['whole_original_text_exact_prefix'] = True
            new_names = set(new) - set(old)
    assert delta['backend/app/adapters/discovery/live_discovery.py']['changed'] == ['LiveDiscoveryAdapter._discover_one', 'LiveDiscoveryAdapter.discover']
    assert delta['backend/app/catalogue/discovery.py']['changed'] == ['CatalogueDiscoveryAdapter._enrich', 'CatalogueDiscoveryAdapter.discover']
    for rel, row in delta.items():
        if rel.startswith('backend/app/'):
            assert row['added'] == []

    junit = {}
    for mode in ['on', 'off']:
        rows = []
        for node in ET.parse(B / f'native.{mode}.final.xml').iter('testcase'):
            base = node.attrib['name'].split('[', 1)[0]
            status = 'ERROR' if node.find('error') is not None else 'FAIL' if node.find('failure') is not None else 'SKIP' if node.find('skipped') is not None else 'PASS'
            rows.append({'class': node.attrib.get('classname'), 'case': node.attrib['name'], 'new': base in new_names, 'status': status})
        junit[mode] = {'rows': rows, 'old_PASS': sum(not r['new'] and r['status'] == 'PASS' for r in rows), 'new_PASS': sum(r['new'] and r['status'] == 'PASS' for r in rows), 'new_FAIL': sum(r['new'] and r['status'] == 'FAIL' for r in rows), 'total': len(rows)}
    assert junit['on']['old_PASS'] == junit['off']['old_PASS'] == 231
    assert junit['on']['new_PASS'] == 19 and junit['off']['new_PASS'] == 12 and junit['off']['new_FAIL'] == 7
    assert junit['on']['total'] == junit['off']['total'] == 250

    off = json.loads((B / 'whole-output.final.off.json').read_text())['rows']
    on = json.loads((B / 'whole-output.final.on.json').read_text())['rows']
    assert set(off) == set(on) and len(on) == 19
    whole_equal = sorted(k for k in on if on[k] == off[k])
    assert len(whole_equal) == 12
    telemetry = ['provider_calls', 'get_reservations', 'read_counts', 'mock_HTTP_exchanges', 'fetcher_stats', 'fetch_tiers', 'separate_walker_outcomes']
    assert all(all(on[k][field] == off[k][field] for field in telemetry) for k in on)
    changed = sorted(set(on) - set(whole_equal))
    for key in changed:
        for before, after in zip(off[key]['captured'], on[key]['captured'], strict=True):
            for a, b in zip(before['candidates'], after['candidates'], strict=True):
                assert {k:v for k,v in a.items() if k != 'search_queries_used'} == {k:v for k,v in b.items() if k != 'search_queries_used'}
                assert not b['programs'] and not b['domain']
    assert all(row.get('exception') is None or row['exception']['same_original_object'] for row in on.values())

    dependency = {p: h for p,h in source['native_dependencies_pre_post'].items() if p.startswith('backend/app/') and (p.endswith('.py') or p == 'backend/app/adapters/search/ontology.json')}
    for mode in ['off', 'on']:
        backend = OWN / 'runtime' / mode / 'backend'
        backend.mkdir(parents=True)
        for rel, digest in dependency.items():
            src = REPO / rel
            assert sha(src) == digest
            dst = backend / rel.removeprefix('backend/')
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        if mode == 'on':
            for rel in source['proposed']:
                if rel.startswith('backend/app/'):
                    (backend / rel.removeprefix('backend/')).write_bytes((B / 'proposed' / rel).read_bytes())
        assert not (backend / '.env').exists()
    result = {'source999_matches': True, 'STOP_unchanged': True, 'minimal_method_delta': delta, 'old_native_test_bodies_and_expectations_unchanged': True, 'author_junit': junit, 'author_whole_output_equalities': whole_equal, 'author_all19_telemetry_equal': True, 'author_changed_only_typed_stop_rows': changed, 'changed_candidates_only_spent_count': True, 'runtime_dependencies': dependency, 'runtime_loading': 'normal own app packages; copied .py plus approved ontology only; no conftest/gold/corpus/DB copy', 'application_imports_in_static_review': 0}
    (OWN / 'static-review.original.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'old_tests_PASS_both': 231, 'new_ON_PASS': 19, 'new_OFF_FAIL': 7, 'whole_equal': len(whole_equal), 'all19_telemetry_equal': True, 'runtime_dependencies': len(dependency)}))


if __name__ == '__main__':
    main()

"""Check exact500 coverage and bind every expert artifact by SHA256."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    all_ids = []
    results = []
    for group in manifest['groups']:
        n = group['group']
        prefix = f'group-{n:02}'
        packet = json.loads((ROOT / f'{prefix}.packet.json').read_text())
        expected = {r['seed_id']: r for r in packet['universities']}
        assert len(expected) == 50
        output = json.loads((ROOT / f'{prefix}.rows.json').read_text())
        rows = output if isinstance(output, list) else next(output[k] for k in ('rows', 'universities', 'results') if isinstance(output.get(k), list))
        assert len(rows) == 50, (n, len(rows))
        assert {r['seed_id'] for r in rows} == set(expected), n
        assert all(r.get('live_checked') is False for r in rows), (n, 'live status missing')
        assert all(r.get('name') == expected[r['seed_id']]['name'] for r in rows), (n, 'name mismatch')
        assert all('tests' in r and 'observations' in r and 'risk' in r for r in rows), (n, 'missing audit fields')
        assert packet['seed_sha256'] == manifest['seed_sha256']
        assert group['status'] == 'complete', (n, 'agent not complete')
        all_ids.extend(r['seed_id'] for r in rows)
        artifacts = {suffix: digest(ROOT / f'{prefix}.{suffix}') for suffix in ('packet.json', 'probe.py', 'rows.json', 'report.md')}
        results.append({'group': n, 'agent': group['agent'], 'audited': len(rows), 'artifacts_sha256': artifacts})
    assert len(all_ids) == len(set(all_ids)) == manifest['count'] == 500
    seed = json.loads((ROOT.parents[2] / 'backend/app/catalogue/unimatch_top500_seed.json').read_text())['universities']
    assert set(all_ids) == {r['seed_id'] for r in seed}
    result = {'status': 'passed', 'groups': len(results), 'universities': len(all_ids), 'unique_universities': len(set(all_ids)), 'live_checked': 0, 'source_sha': manifest['source_sha'], 'seed_sha256': manifest['seed_sha256'], 'groups_evidence': results, 'limits': 'Artifact integrity and audit coverage only; no admission fact certification or live search acceptance'}
    (ROOT / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='groups_evidence'},indent=2))


if __name__ == '__main__':
    main()

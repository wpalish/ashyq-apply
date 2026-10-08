"""Finite stdlib hash/size/origin audit; no app imports, tests or Git."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = ROOT / 'work/ashyq-apply'
OWN = Path(__file__).resolve().parent
NATIVE = ROOT / 'work/local-round13/root-stopped-trace-accounting'
ARCHIVES = REPO / 'docs/process/evidence/search-loop/2026-10-07/local-round13'
RUN = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T053629Z-check-6693acd5')
STOP = ROOT / 'work/local-round7/provider-STOP.json'
STOP_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
ACCEPTED = {
    'backend/app/adapters/discovery/live_discovery.py': '57cfdab71d29e261c6ca18652ba69c4b018954780eab8d00f62f9f55c26ee093',
    'backend/app/catalogue/discovery.py': 'bc07cdaf263349931dbb7abb3d987897480711ecb4b19420ce5f2e5df70eda12',
    'backend/tests/test_live_discovery.py': 'aef28ed47c9f8f2ee84d878c405ba442a2c89340464a3695b20567317c39863e',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_state():
    saved = json.loads((NATIVE / 'source-after-999.json').read_text())['file_sha256']
    before = json.loads((NATIVE / 'source-before-999.json').read_text())['file_sha256']
    frozen = json.loads((RUN / 'source-manifest.json').read_text())
    assert frozen['source_head'] == 'ab273163d73f3fc6af78b7ebbee47d6863044aa3'
    assert frozen['source_tree_sha256'] == '75497406d33bb8c4fe3015d44b13e20786d8cf9a74d4e6138c16d3341164d446'
    assert len(saved) == len(before) == 999 and set(saved) == set(before)
    changed = {rel for rel in saved if saved[rel] != before[rel]}
    assert changed == set(ACCEPTED)
    assert all(saved[rel] == digest for rel, digest in ACCEPTED.items())
    mismatches = []
    for rel, digest in saved.items():
        primary = REPO / rel
        snapshot = RUN / 'source' / rel
        if sha(primary) != digest or sha(snapshot) != digest or frozen['files'][rel] != digest or primary.read_bytes() != snapshot.read_bytes():
            mismatches.append(rel)
    assert not mismatches and sha(STOP) == STOP_SHA
    return {'source999_primary_frozen_saved_equal': True, 'selected_paths': len(saved), 'changed_exactly_accepted3': sorted(changed), 'unchanged_other_paths': 996, 'source_after_map_sha256': sha(NATIVE / 'source-after-999.json'), 'frozen_manifest_sha256': sha(RUN / 'source-manifest.json'), 'frozen_source_tree_sha256': frozen['source_tree_sha256'], 'frozen_source_head': frozen['source_head'], 'STOP_sha256': sha(STOP)}


def main():
    before = source_state()
    proposal = ROOT / 'work/local-round13/b-stopped-trace-proposal'
    peer = ROOT / 'work/local-round13/a-stopped-trace-peer-review'
    assert sha(proposal / 'ready-manifest.json') == 'b95a950c8cfc3cee5583dbe17d6a0f66843dbcc8e41db674bff38b620a558872'
    assert sha(peer / 'ready-manifest.json') == 'c9c6ba029d29c98d0797be1285c2e7c7bb4a95eac27c7143993d2bcc1077378e'
    for rel, digest in ACCEPTED.items():
        assert sha(proposal / 'proposed' / rel) == digest == sha(REPO / rel)
    old_test = proposal / 'original/backend/tests/test_live_discovery.py'
    new_test = REPO / 'backend/tests/test_live_discovery.py'
    assert new_test.read_bytes().startswith(old_test.read_bytes())

    seed = ROOT / 'work/local-round13/b-stopped-trace-seed'
    seed_map = seed / 'candidate-app-pins.json'
    binding = json.loads((NATIVE / 'seed-primary-binding.json').read_text())
    assert sha(seed / 'ready-manifest.json') == binding['seed_ready_sha256'] == 'db5c5ac3a02c840c1522340f3eb105e6f202a41f73c9ce9e014fcfb87dbddd4e'
    assert sha(seed_map) == binding['candidate_app_map_file_sha256'] == '7bbe2bf9db9c719ad85cd8be127129046234dfb0b3c80644df31d27aa5b84144'
    app = json.loads(seed_map.read_text())
    assert len(app) == binding['appfiles'] == 242
    assert all(sha(REPO / rel) == digest == sha(RUN / 'source' / rel) for rel, digest in app.items())

    groups = [('stopped-trace-off-proof', 39), ('stopped-trace-compatibility', 25), ('stopped-trace-proposal', 80), ('stopped-trace-peer', 99), ('stopped-trace-seed', 25)]
    archives = []
    inputs = []
    for label, count in groups:
        folder = ARCHIVES / label
        receipt = folder / 'receipt.json'
        data = json.loads(receipt.read_text())
        rows = data['file_sha256']
        assert len(rows) == data['selected_files'] == count
        assert sum(r['bytes'] for r in rows.values()) == data['selected_bytes']
        assert data['STOP_sha256'] == STOP_SHA and data['source_prefix_selected_paths_matched'] == 999
        physical = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
        assert physical == set(rows) | {'receipt.json'}
        for rel, row in rows.items():
            copy = folder / rel
            original = Path(row['original'])
            assert sha(copy) == row['sha256'] == sha(original)
            assert copy.stat().st_size == original.stat().st_size == row['bytes']
            assert copy.read_bytes() == original.read_bytes()
        origin_rows = []
        for origin in data['origins']:
            source = ROOT / 'work' / origin['folder']
            manifest = source / 'ready-manifest.json'
            assert sha(manifest) == origin['manifest_sha256']
            native = json.loads(manifest.read_text())
            assert origin['physical_selected_files'] == len(native['files']) + 1
            for rel, row in native['files'].items():
                p = source / rel
                assert sha(p) == row['sha256'] and p.stat().st_size == row['bytes']
            origin_rows.append({'folder': str(source), 'manifest_sha256': sha(manifest), 'physical_selected_files': origin['physical_selected_files'], 'all_origin_sealed_members_verified': True})
        archives.append({'archive': label, 'receipt_sha256': sha(receipt), 'selected_originals': count, 'selected_bytes': data['selected_bytes'], 'physical_files_including_archive_receipt': len(physical), 'all_SHA_size_copy_original_equal': True, 'physical_membership_exact': True, 'origins': origin_rows, 'original_receipt_status': data['status'], 'qualification': 'Original pending/preparation status retained; physical copies are not distinct experiments.'})
        inputs.append(receipt)

    primary = ARCHIVES / 'stopped-trace-primary'
    names = ['source-after-999.json', 'source-integration.json', 'seed-primary-binding.json']
    assert {p.name for p in primary.iterdir() if p.is_file()} == set(names)
    primary_rows = []
    for name in names:
        copy, original = primary / name, NATIVE / name
        assert copy.read_bytes() == original.read_bytes()
        primary_rows.append({'file': name, 'sha256': sha(copy), 'bytes': copy.stat().st_size, 'original': str(original), 'copy_exact': True})
    assert json.loads((primary / 'source-integration.json').read_text())['applied'] == {rel: {'sha256': digest, 'bytes': (REPO / rel).stat().st_size} for rel, digest in ACCEPTED.items()}
    after = source_state()
    assert after == before

    # Retain only finite hash/origin metadata, never corpus or native full DB.
    input_folder = OWN / 'inputs'
    input_folder.mkdir()
    inputs += [NATIVE / name for name in names] + [NATIVE / 'source-before-999.json', seed_map]
    input_pins = []
    for index, p in enumerate(inputs):
        target = input_folder / f'{index+1}-{p.parent.name}-{p.name}'
        target.write_bytes(p.read_bytes())
        input_pins.append({'copy': str(target.relative_to(OWN)), 'original': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size})
    result = {'time': datetime.now(UTC).isoformat(), 'status': 'PASS_FINITE_HASH_ORIGIN_INTEGRATION_AUDIT_ONLY', 'source_before': before, 'source_after': after, 'accepted3_exact': ACCEPTED, 'old_test_whole_byte_prefix_preserved': True, 'seed_app242_primary_frozen_binding_exact': True, 'seed_map_sha256': sha(seed_map), 'archives': archives, 'primary_metadata3': primary_rows, 'selected_archive_originals_including_primary': sum(count for _,count in groups) + len(primary_rows), 'inputs': input_pins, 'source_metadata_read_only': True, 'full_status_at_assignment': 'RUNNING; NOT_A_FULL_PASS_CLAIM; FINAL_RAW_REVIEW_ASSIGNED_TO_B', 'app_imports_tests_SQL_Git_network_gold_scoring': 0, 'semantic_controls_rerun': 0, 'counts_qualification': '271 physical selected originals are copies, not experiments. Nested peer/source copies do not add unique control executions.'}
    (OWN / 'audit.original.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'source999_equal': True, 'accepted3_exact_other996_unchanged': True, 'seed242_equal': True, 'archive_groups': len(archives), 'selected_originals_including_primary': result['selected_archive_originals_including_primary'], 'STOP_unchanged': True, 'application_imports_tests': 0, 'full_PASS_claim': False}))


if __name__ == '__main__':
    main()
